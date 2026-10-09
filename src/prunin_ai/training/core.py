from __future__ import annotations
import json
import warnings
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import yaml
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, classification_report,
    confusion_matrix, f1_score, mean_absolute_error,
    mean_squared_error, median_absolute_error, precision_score,
    r2_score, recall_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from ..constants import STATIC_NUMERIC_FEATURES, CATEGORICAL_FEATURES, CORE_TEMPORAL_FEATURES
from ..targets import add_targets


def _split_groups(df: pd.DataFrame, seed: int):
    groups = df["project_id"].astype(str)
    first = GroupShuffleSplit(n_splits=1, train_size=0.70, random_state=seed)
    train_idx, temp_idx = next(first.split(df, groups=groups))
    temp = df.iloc[temp_idx]
    temp_groups = temp["project_id"].astype(str)
    second = GroupShuffleSplit(n_splits=1, train_size=0.50, random_state=seed + 1)
    val_rel, test_rel = next(second.split(temp, groups=temp_groups))
    return train_idx, temp_idx[val_rel], temp_idx[test_rel]


def _indices_from_manifest(df: pd.DataFrame, split_manifest: dict):
    required = {"train", "validation", "test"}
    if set(split_manifest) != required:
        raise ValueError("El split manifest debe contener train, validation y test.")
    project_ids = df["project_id"].astype(str)
    project_sets = {name: set(map(str, split_manifest[name])) for name in required}
    if not project_sets["train"].isdisjoint(project_sets["validation"]):
        raise RuntimeError("Leakage: train_project_ids.isdisjoint(validation_project_ids) falló.")
    if not project_sets["train"].isdisjoint(project_sets["test"]):
        raise RuntimeError("Leakage: train_project_ids.isdisjoint(test_project_ids) falló.")
    if not project_sets["validation"].isdisjoint(project_sets["test"]):
        raise RuntimeError("Leakage: validation_project_ids.isdisjoint(test_project_ids) falló.")
    if set(project_ids) != set.union(*project_sets.values()):
        raise ValueError("El split manifest no cubre exactamente los proyectos del dataset.")
    indices = tuple(
        np.flatnonzero(project_ids.isin(project_sets[name]).to_numpy())
        for name in ("train", "validation", "test")
    )
    return indices


def _feature_sets(df: pd.DataFrame):
    numeric_candidates = STATIC_NUMERIC_FEATURES + CORE_TEMPORAL_FEATURES
    numeric = [c for c in numeric_candidates if c in df.columns and df[c].notna().any()]
    categorical = [c for c in CATEGORICAL_FEATURES if c in df.columns and df[c].notna().any()]
    return numeric, categorical


def _preprocessor(numeric: list[str], categorical: list[str]):
    transformers = []
    if numeric:
        transformers.append(("num", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
        ]), numeric))
    if categorical:
        transformers.append(("cat", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), categorical))
    if not transformers:
        raise ValueError("No hay features utilizables para entrenar.")
    return ColumnTransformer(transformers, remainder="drop")


def _classifier(cfg: dict, seed: int):
    p = cfg["model"]["classification"]
    return LGBMClassifier(
        objective="multiclass",
        n_estimators=int(p["n_estimators"]), learning_rate=float(p["learning_rate"]),
        num_leaves=int(p["num_leaves"]), max_depth=int(p["max_depth"]),
        min_child_samples=int(p["min_child_samples"]), reg_alpha=float(p["reg_alpha"]),
        reg_lambda=float(p["reg_lambda"]), class_weight="balanced", random_state=seed,
        n_jobs=-1, verbosity=-1,
    )


def _regressor(cfg: dict, seed: int):
    p = cfg["model"]["regression"]
    return LGBMRegressor(
        objective="regression_l1",
        n_estimators=int(p["n_estimators"]), learning_rate=float(p["learning_rate"]),
        num_leaves=int(p["num_leaves"]), max_depth=int(p["max_depth"]),
        min_child_samples=int(p["min_child_samples"]), reg_alpha=float(p["reg_alpha"]),
        reg_lambda=float(p["reg_lambda"]), random_state=seed, n_jobs=-1, verbosity=-1,
    )


def _classification_metrics(y_true, y_pred, labels=None):
    labels = list(labels if labels is not None else sorted(set(y_true) | set(y_pred)))
    names = [str(label) for label in labels]
    report = classification_report(
        y_true, y_pred, labels=labels, target_names=names,
        output_dict=True, zero_division=0,
    )
    per_class = {
        name: {
            "precision": float(report[name]["precision"]),
            "recall": float(report[name]["recall"]),
            "f1": float(report[name]["f1-score"]),
            "support": int(report[name]["support"]),
        }
        for name in names
    }
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)),
        "precision_macro": float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "precision_weighted": float(precision_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)),
        "recall_weighted": float(recall_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)),
        "labels": names,
        "per_class": per_class,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "classification_report": report,
    }


def _regression_metrics(y_true, y_pred):
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    absolute_errors = np.abs(actual - predicted)
    result = {
        "mae": float(mean_absolute_error(actual, predicted)),
        "median_absolute_error": float(median_absolute_error(actual, predicted)),
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "r2": float(r2_score(y_true, y_pred)),
        "absolute_error_percentiles": {
            f"p{percentile}": float(np.percentile(absolute_errors, percentile))
            for percentile in (50, 75, 90, 95)
        },
    }
    if np.all(actual > 0):
        result["mape_percent"] = float(np.mean(absolute_errors / actual) * 100)
        result["mape_status"] = "reported; all actual values are positive"
    else:
        result["mape_percent"] = None
        result["mape_status"] = "not reported; target contains zero or negative actual values"
    return result


def _project_latest_snapshots(frame: pd.DataFrame) -> pd.DataFrame:
    order = ["project_id"]
    if "snapshot_index" in frame.columns:
        order.append("snapshot_index")
    return frame.sort_values(order, kind="stable").groupby("project_id", sort=False).tail(1)


def _model_tasks(final_status_mode: str) -> list[tuple[str, str]]:
    tasks = [("health", "classification")]
    if final_status_mode != "derived_from_health":
        tasks.append(("final_status", "classification"))
    tasks.extend([("delay_days", "regression"), ("cost_overrun_ratio", "regression")])
    return tasks


def _feature_importance(model_pipe: Pipeline, artifact_dir: Path, model_name: str) -> None:
    estimator = model_pipe.named_steps["model"]
    preprocessor = model_pipe.named_steps["prep"]
    names = preprocessor.get_feature_names_out()
    split_values = estimator.booster_.feature_importance(importance_type="split")
    gain_values = estimator.booster_.feature_importance(importance_type="gain")
    importance = pd.DataFrame({
        "raw_feature": names,
        "display_feature": [_display_feature_name(str(name)) for name in names],
        "gain": gain_values,
        "split": split_values,
    }).sort_values(["gain", "split"], ascending=False, kind="stable")
    importance["gain_fraction"] = importance["gain"] / max(float(importance["gain"].sum()), 1.0)
    importance.insert(0, "rank", np.arange(1, len(importance) + 1))
    report_name = {
        "health": "health",
        "final_status": "final_status",
        "delay_days": "delay",
        "cost_overrun_ratio": "cost",
    }.get(model_name, model_name)
    importance.to_csv(artifact_dir / f"feature_importance_{report_name}.csv", index=False)

def _display_feature_name(raw_name: str) -> str:
    if raw_name.startswith("num__"):
        return raw_name.removeprefix("num__")
    if raw_name.startswith("cat__"):
        feature = raw_name.removeprefix("cat__")
        categories = ("methodology", "project_type", "sector", "complexity", "criticality")
        for name in categories:
            prefix = f"{name}_"
            if feature.startswith(prefix):
                return f"{name} = {feature.removeprefix(prefix)}"
        return feature
    return raw_name


def _business_status(health: pd.Series) -> pd.Series:
    return health.map({"healthy": "successful", "at_risk": "challenged", "critical": "critical"})


def _build_baseline_reports(splits: dict[str, pd.DataFrame], model_metrics: dict) -> tuple[dict, pd.DataFrame]:
    train_projects = _project_latest_snapshots(splits["train"])
    results = {}
    comparisons = []
    for target in ("health", "delay_days", "cost_overrun_ratio"):
        train_values = train_projects[target].dropna()
        if train_values.empty:
            results[target] = {"status": "unavailable", "reason": "no train project targets"}
            continue
        if target == "health":
            method = "majority_class_from_train_projects"
            class_counts = train_values.astype(str).value_counts().sort_index()
            baseline_value = str(class_counts.idxmax())
        else:
            method = "median_from_train_projects"
            baseline_value = float(pd.to_numeric(train_values, errors="coerce").median())
        target_result = {"status": "computed", "method": method, "train_project_count": int(len(train_values)),
                         "train_statistic": baseline_value, "validation": {}, "test": {}}
        for split_name in ("validation", "test"):
            split_rows = splits[split_name].dropna(subset=[target])
            split_projects = _project_latest_snapshots(split_rows)
            project_y = split_projects[target]
            project_prediction = np.repeat(baseline_value, len(split_projects))
            if target == "health":
                labels = list(class_counts.index.astype(str))
                project_metric = _classification_metrics(project_y.astype(str), project_prediction, labels)
                row_metric = _classification_metrics(
                    split_rows[target].astype(str), np.repeat(baseline_value, len(split_rows)), labels
                )
            else:
                project_metric = _regression_metrics(project_y, project_prediction)
                row_metric = _regression_metrics(
                    split_rows[target], np.repeat(baseline_value, len(split_rows))
                )
                if target == "cost_overrun_ratio":
                    project_metric["mae_percentage_points"] = project_metric["mae"] * 100
                    row_metric["mae_percentage_points"] = row_metric["mae"] * 100
            target_result[split_name] = {
                "snapshot_row_metrics": row_metric,
                "project_level_metrics": project_metric,
                "project_count": int(split_projects["project_id"].nunique()),
            }
        model_project_test = model_metrics.get(target, {}).get("project_level_metrics", {}).get("test") or {}
        baseline_project_test = target_result.get("test", {}).get("project_level_metrics", {})
        compare_metric = (
            "macro_f1" if target == "health"
            else "mae_percentage_points" if target == "cost_overrun_ratio"
            else "mae"
        )
        model_value = model_project_test.get(compare_metric)
        baseline_value_metric = baseline_project_test.get(compare_metric)
        improvement = (
            model_value - baseline_value_metric if target == "health"
            else baseline_value_metric - model_value
        ) if model_value is not None and baseline_value_metric is not None else None
        target_result["project_level_test_model"] = model_project_test
        target_result["project_level_test_improvement"] = {
            "metric": compare_metric,
            "positive_is_better": True,
            "model_minus_baseline": improvement,
            "decision_source": "test is descriptive only; baseline statistic was fitted using TRAIN projects",
        }
        results[target] = target_result
        unit = "macro_f1" if target == "health" else "mae_percentage_points" if target == "cost_overrun_ratio" else "mae"
        model_test = model_project_test.get(unit)
        base_test = baseline_project_test.get(unit)
        comparisons.append({
            "target": target,
            "evaluation_unit": "project_level_test",
            "metric": unit,
            "baseline_method": method,
            "baseline_value": base_test,
            "model_value": model_test,
            "improvement_positive_is_better": (
                model_test - base_test if target == "health" and model_test is not None and base_test is not None
                else base_test - model_test if model_test is not None and base_test is not None else None
            ),
            "baseline_fit_split": "train only",
        })
    return results, pd.DataFrame(comparisons)


def train_core(
    df: pd.DataFrame,
    cfg: dict,
    artifact_dir: str | Path,
    split_manifest: dict | None = None,
) -> dict:
    if "project_id" not in df.columns:
        raise ValueError("El dataset requiere project_id para un split sin leakage.")

    data = add_targets(df, cfg["target_rules"])
    numeric, categorical = _feature_sets(data)
    features = numeric + categorical
    seed = int(cfg.get("random_seed", 42))
    train_idx, val_idx, test_idx = (
        _indices_from_manifest(data, split_manifest)
        if split_manifest is not None else _split_groups(data, seed)
    )
    splits = {"train": data.iloc[train_idx], "validation": data.iloc[val_idx], "test": data.iloc[test_idx]}

    # Verificación explícita de no leakage entre proyectos.
    project_sets = {k: set(v["project_id"].astype(str)) for k, v in splits.items()}
    if not project_sets["train"].isdisjoint(project_sets["validation"]):
        raise RuntimeError("Leakage: train_project_ids.isdisjoint(validation_project_ids) falló.")
    if not project_sets["train"].isdisjoint(project_sets["test"]):
        raise RuntimeError("Leakage: train_project_ids.isdisjoint(test_project_ids) falló.")
    if not project_sets["validation"].isdisjoint(project_sets["test"]):
        raise RuntimeError("Leakage: project_id aparece en más de un split.")

    forbidden_features = {
        "health", "final_status", "delay_days", "cost_overrun_ratio",
        "actual_duration", "actual_duration_days", "actual_duration_months",
        "actual_cost", "cost_overrun", "schedule_delay", "schedule_delay_days",
    }
    leaked = forbidden_features.intersection(features)
    if leaked:
        raise RuntimeError(f"Target leakage en features: {sorted(leaked)}")

    out = Path(artifact_dir)
    out.mkdir(parents=True, exist_ok=True)
    metrics = {}
    mendeley_only = (
        "data_source" in data
        and set(data["data_source"].dropna().astype(str)) == {"mendeley_2p5sz57wh2_v2"}
    )

    final_status_mode = "derived_from_health" if mendeley_only else "independent_model"
    tasks = _model_tasks(final_status_mode)
    predictions = None

    for target, kind in tasks:
        tr = splits["train"].dropna(subset=[target])
        va = splits["validation"].dropna(subset=[target])
        te = splits["test"].dropna(subset=[target])
        if tr.empty or te.empty:
            metrics[target] = {"status": "skipped", "reason": "target sin cobertura suficiente"}
            continue
        if kind == "classification" and tr[target].nunique() < 2:
            metrics[target] = {"status": "skipped", "reason": "menos de dos clases en train"}
            continue

        model = _classifier(cfg, seed) if kind == "classification" else _regressor(cfg, seed)
        pipe = Pipeline([("prep", _preprocessor(numeric, categorical)), ("model", model)])
        pipe.fit(tr[features], tr[target])
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"X does not have valid feature names.*", category=UserWarning)
            pred_val = pipe.predict(va[features]) if len(va) else np.array([])
            pred_test = pipe.predict(te[features])
        if kind == "classification":
            labels = list(model.classes_)
            row_validation = _classification_metrics(va[target], pred_val, labels) if len(va) else None
            row_test = _classification_metrics(te[target], pred_test, labels)
        else:
            row_validation = _regression_metrics(va[target], pred_val) if len(va) else None
            row_test = _regression_metrics(te[target], pred_test)
            if target == "cost_overrun_ratio":
                row_validation["mae_percentage_points"] = row_validation["mae"] * 100 if row_validation else None
                row_test["mae_percentage_points"] = row_test["mae"] * 100
        project_validation = _project_latest_snapshots(va) if len(va) else va
        project_test = _project_latest_snapshots(te)
        if len(project_validation):
            project_val_pred = pipe.predict(project_validation[features])
        else:
            project_val_pred = np.array([])
        project_test_pred = pipe.predict(project_test[features])
        if kind == "classification":
            project_validation_metrics = (
                _classification_metrics(project_validation[target], project_val_pred, labels)
                if len(project_validation) else None
            )
            project_test_metrics = _classification_metrics(project_test[target], project_test_pred, labels)
        else:
            project_validation_metrics = (
                _regression_metrics(project_validation[target], project_val_pred)
                if len(project_validation) else None
            )
            project_test_metrics = _regression_metrics(project_test[target], project_test_pred)
            if target == "cost_overrun_ratio":
                if project_validation_metrics:
                    project_validation_metrics["mae_percentage_points"] = project_validation_metrics["mae"] * 100
                project_test_metrics["mae_percentage_points"] = project_test_metrics["mae"] * 100
        metrics[target] = {
            "status": "trained",
            "evaluation_unit": "snapshot rows; each project can contribute multiple snapshots",
            "validation": row_validation,
            "test": row_test,
            "row_level_metrics": {"validation": row_validation, "test": row_test},
            "project_level_metrics": {
                "method": "latest available snapshot per project within the split",
                "validation": project_validation_metrics,
                "test": project_test_metrics,
                "validation_project_count": int(project_validation["project_id"].nunique()),
                "test_project_count": int(project_test["project_id"].nunique()),
            },
            "train_rows": int(len(tr)), "validation_rows": int(len(va)), "test_rows": int(len(te)),
        }
        joblib.dump(pipe, out / f"{target}.joblib")
        _feature_importance(pipe, out, target)
        if target == "health":
            predictions = project_test[[
                column for column in ("project_id", "source_project_id", "snapshot_index", "true_progress")
                if column in project_test
            ]].copy()
            predictions["actual_health"] = project_test["health"].astype(str).to_numpy()
            predictions["predicted_health"] = project_test_pred
        elif target == "final_status" and predictions is not None:
            predictions["actual_final_status"] = project_test[target].astype(str).to_numpy()
            predictions["predicted_final_status"] = project_test_pred
        elif target in {"delay_days", "cost_overrun_ratio"} and predictions is not None:
            suffix = "delay_days" if target == "delay_days" else "cost_overrun_ratio"
            predictions[f"actual_{suffix}"] = project_test[target].to_numpy()
            predictions[f"predicted_{suffix}"] = project_test_pred

    if mendeley_only:
        metrics["final_status"] = {
            "status": "derived",
            "source": "health",
            "mapping": {"healthy": "successful", "at_risk": "challenged", "critical": "critical"},
            "note": "Mendeley v2 has no independent final-status column; no redundant classifier was trained.",
        }
        if predictions is not None:
            predictions["actual_final_status"] = _business_status(predictions["actual_health"]).to_numpy()
            predictions["predicted_final_status"] = _business_status(predictions["predicted_health"]).to_numpy()
    if predictions is not None:
        predictions.to_csv(out / "test_project_predictions.csv", index=False)

    baselines, baseline_comparison = _build_baseline_reports(splits, metrics)
    (out / "baselines.json").write_text(json.dumps(baselines, indent=2, ensure_ascii=False), encoding="utf-8")
    baseline_comparison.to_csv(out / "baseline_comparison.csv", index=False)

    manifest = {
        "schema_version": "v9-academic",
        "dataset_source": "Mendeley Data 2p5sz57wh2 version 2" if mendeley_only else "generated dataset source",
        "dataset_type": "synthetic external data" if mendeley_only else "synthetic demo data",
        "model_type": "LightGBM",
        "numeric_features": numeric,
        "categorical_features": categorical,
        "excluded_from_v863": ["reported_progress", "critical_path_delay_days", "team_morale"],
        "operational_derived": ["team_health_index"],
        "target_columns_excluded": sorted(forbidden_features),
        "target_leakage_check": {"status": "passed", "feature_overlap": []},
        "final_status_mode": final_status_mode,
        "target_leakage_review": {
            "direct_leakage": "pass",
            "temporal_proximity_risk": "SPI, CPI, and progress may be close to final outcomes in late snapshots; see cutoff-specific temporal evaluation.",
            "excluded_columns": sorted(forbidden_features),
            "notes": "No raw final outcome fields enter the feature whitelist. Project-grouped split prevents cross-project leakage.",
        },
        "note": "team_health_index se fusiona operativamente; sólo será feature supervisada cuando exista data histórica emparejada con outcomes.",
    }
    split_manifest = {k: sorted(v) for k, v in project_sets.items()}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "feature_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "split_manifest.json").write_text(json.dumps(split_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "training_config_resolved.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return {"metrics": metrics, "manifest": manifest, "splits": {k: len(v) for k, v in splits.items()}}
