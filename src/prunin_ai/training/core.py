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
    accuracy_score, balanced_accuracy_score, f1_score,
    mean_absolute_error, mean_squared_error, r2_score,
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


def _classification_metrics(y_true, y_pred):
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
    }


def _regression_metrics(y_true, y_pred):
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "r2": float(r2_score(y_true, y_pred)),
    }


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

    tasks = [
        ("health", "classification"),
        ("final_status", "classification"),
        ("delay_days", "regression"),
        ("cost_overrun_ratio", "regression"),
    ]

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
        calc = _classification_metrics if kind == "classification" else _regression_metrics
        metrics[target] = {
            "status": "trained",
            "validation": calc(va[target], pred_val) if len(va) else None,
            "test": calc(te[target], pred_test),
            "train_rows": int(len(tr)), "validation_rows": int(len(va)), "test_rows": int(len(te)),
        }
        joblib.dump(pipe, out / f"{target}.joblib")

    manifest = {
        "schema_version": "v9-academic",
        "numeric_features": numeric,
        "categorical_features": categorical,
        "excluded_from_v863": ["reported_progress", "critical_path_delay_days", "team_morale"],
        "operational_derived": ["team_health_index"],
        "target_columns_excluded": sorted(forbidden_features),
        "target_leakage_check": {"status": "passed", "feature_overlap": []},
        "note": "team_health_index se fusiona operativamente; sólo será feature supervisada cuando exista data histórica emparejada con outcomes.",
    }
    split_manifest = {k: sorted(v) for k, v in project_sets.items()}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "feature_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "split_manifest.json").write_text(json.dumps(split_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "training_config_resolved.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return {"metrics": metrics, "manifest": manifest, "splits": {k: len(v) for k, v in splits.items()}}
