#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prunin_ai.config import load_config
from prunin_ai.training.core import _preprocessor, _project_latest_snapshots, _regression_metrics

REPORT_DIR = ROOT / "reports/experiments/delay"


def select_delay_candidate(validation_metrics: dict[str, dict], rmse_guard_ratio: float = 1.10) -> dict:
    current = validation_metrics["lightgbm_current"]
    allowed_candidates = {
        "lightgbm_moderate_tuning", "hist_gradient_boosting",
        "median_train_project_baseline", "spi_evm_remaining_duration_rule",
    }
    eligible = [
        (name, result) for name, result in validation_metrics.items()
        if name in allowed_candidates
        and result.get("mae") is not None
        and result.get("rmse") is not None
        and result["mae"] < current["mae"]
        and result["rmse"] <= current["rmse"] * rmse_guard_ratio
    ]
    if not eligible:
        return {
            "selected_candidate": "lightgbm_current",
            "selection_status": "No candidate exceeded the current model under validation criteria.",
            "selection_metric": "validation project-level MAE; RMSE may not exceed current by more than 10%",
        }
    selected_name, selected_metrics = min(eligible, key=lambda item: (item[1]["mae"], item[1]["rmse"]))
    return {
        "selected_candidate": selected_name,
        "selection_status": "candidate selected on validation only; automatic promotion disabled",
        "selection_metric": "validation project-level MAE; RMSE guard applied",
        "selected_validation_metrics": selected_metrics,
    }


def _spi_evm_rule(frame: pd.DataFrame) -> np.ndarray:
    required = {"planned_duration_weeks", "true_progress", "spi"}
    if not required <= set(frame.columns):
        return np.full(len(frame), np.nan)
    duration_days = pd.to_numeric(frame["planned_duration_weeks"], errors="coerce") * 7.0
    progress = pd.to_numeric(frame["true_progress"], errors="coerce").clip(0, 1)
    spi = pd.to_numeric(frame["spi"], errors="coerce").clip(lower=0.1)
    # Remaining planned duration is scaled by schedule efficiency; reported delay is non-negative.
    forecast_delay = duration_days * (1 - progress) * (1 / spi - 1)
    return forecast_delay.clip(lower=0).fillna(0).to_numpy(dtype=float)


def run_delay_experiment(input_path: Path, artifact_dir: Path, output_dir: Path = REPORT_DIR) -> dict:
    readiness = json.loads((artifact_dir / "data_readiness.json").read_text(encoding="utf-8"))
    split = json.loads((artifact_dir / "split_manifest.json").read_text(encoding="utf-8"))
    if not readiness.get("ready_for_training") or readiness.get("leakage_check", {}).get("status") != "passed":
        raise RuntimeError("Delay experiment blocked: data readiness/leakage gate did not pass.")
    data = pd.read_csv(input_path, low_memory=False)
    data["project_id"] = data["project_id"].astype(str)
    train = data[data["project_id"].isin(set(split["train"]))].copy()
    validation = data[data["project_id"].isin(set(split["validation"]))].copy()
    test = data[data["project_id"].isin(set(split["test"]))].copy()
    train_projects = _project_latest_snapshots(train).dropna(subset=["delay_days"])
    validation_projects = _project_latest_snapshots(validation).dropna(subset=["delay_days"])
    test_projects = _project_latest_snapshots(test).dropna(subset=["delay_days"])
    feature_manifest = json.loads((artifact_dir / "feature_manifest.json").read_text(encoding="utf-8"))
    features = feature_manifest["numeric_features"] + feature_manifest["categorical_features"]
    config = load_config(ROOT / "configs/training.yaml")
    seed = int(config.get("random_seed", 42))
    current_model = joblib.load(artifact_dir / "delay_days.joblib")
    current_predictions = current_model.predict(validation_projects[features])
    validation_metrics = {
        "lightgbm_current": _regression_metrics(validation_projects["delay_days"], current_predictions)
    }
    candidate_models = {}

    regression_cfg = config["model"]["regression"]
    tuned = LGBMRegressor(
        objective="regression_l1", n_estimators=max(100, int(regression_cfg["n_estimators"] * 0.75)),
        learning_rate=float(regression_cfg["learning_rate"]), num_leaves=15, max_depth=5,
        min_child_samples=max(30, int(regression_cfg["min_child_samples"])),
        reg_alpha=float(regression_cfg["reg_alpha"]), reg_lambda=float(regression_cfg["reg_lambda"]),
        random_state=seed, n_jobs=-1, verbosity=-1,
    )
    candidate_models["lightgbm_moderate_tuning"] = Pipeline([
        ("prep", _preprocessor(feature_manifest["numeric_features"], feature_manifest["categorical_features"])),
        ("model", tuned),
    ])
    hist = HistGradientBoostingRegressor(
        max_iter=100, max_leaf_nodes=15, l2_regularization=1.0, random_state=seed,
    )
    candidate_models["hist_gradient_boosting"] = Pipeline([
        ("prep", _preprocessor(feature_manifest["numeric_features"], feature_manifest["categorical_features"])),
        ("model", hist),
    ])
    train_rows = train.dropna(subset=["delay_days"])
    y_train = train_rows["delay_days"].astype(float)
    median_train_project_delay = float(train_projects["delay_days"].median())
    validation_metrics["median_train_project_baseline"] = _regression_metrics(
        validation_projects["delay_days"], np.full(len(validation_projects), median_train_project_delay)
    )
    rule_predictions = _spi_evm_rule(validation_projects)
    validation_metrics["spi_evm_remaining_duration_rule"] = _regression_metrics(
        validation_projects["delay_days"], rule_predictions
    )
    for name, pipeline in candidate_models.items():
        pipeline.fit(train_rows[features], y_train)
        prediction = pipeline.predict(validation_projects[features])
        validation_metrics[name] = _regression_metrics(validation_projects["delay_days"], prediction)

    decision = select_delay_candidate(validation_metrics)
    selected = decision["selected_candidate"]
    if selected == "lightgbm_current":
        test_predictions = current_model.predict(test_projects[features])
        test_source = "reused locked test result from standard evaluation; no tuning used TEST"
    elif selected == "spi_evm_remaining_duration_rule":
        test_predictions = _spi_evm_rule(test_projects)
        test_source = "single evaluation of validation-selected analytical rule"
    elif selected == "median_train_project_baseline":
        test_predictions = np.full(len(test_projects), median_train_project_delay)
        test_source = "single evaluation of validation-selected train-median baseline"
    else:
        test_predictions = candidate_models[selected].predict(test_projects[features])
        test_source = "single evaluation of candidate selected using validation only"
    selected_test_metrics = _regression_metrics(test_projects["delay_days"], test_predictions)
    test_metrics = {
        "selected_candidate": selected,
        "test_project_count": int(test_projects["project_id"].nunique()),
        "metrics": selected_test_metrics,
        "evaluation_note": test_source,
    }
    result = {
        "experiment": "Delay model candidates",
        "selection_split": "validation project-level only",
        "test_policy": "TEST is used once after the validation selection is frozen; never used for tuning.",
        "train_project_count": int(train_projects["project_id"].nunique()),
        "validation_project_count": int(validation_projects["project_id"].nunique()),
        "test_project_count": int(test_projects["project_id"].nunique()),
        "baseline_fit": {
            "delay_median": median_train_project_delay,
            "fit_unit": "latest available snapshot per TRAIN project only",
        },
        "rule_definition": "max(0, planned_duration_days * (1 - true_progress) * (1 / max(SPI, 0.1) - 1)); EVM remaining-duration projection, not a learned outcome",
        "validation_candidates": validation_metrics,
        "decision": decision,
        "test_evaluation_after_freeze": test_metrics,
        "promoted_to_delay_days_joblib": False,
        "promotion_note": "The current artifact is never replaced automatically by this experiment.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "comparison.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    comparison_rows = []
    current_val = validation_metrics["lightgbm_current"]
    for name, candidate in validation_metrics.items():
        comparison_rows.append({
            "candidate": name,
            "validation_project_mae_days": candidate["mae"],
            "validation_project_rmse_days": candidate["rmse"],
            "validation_project_r2": candidate["r2"],
            "current_validation_mae_days": current_val["mae"],
            "mae_improvement_vs_current_days": current_val["mae"] - candidate["mae"],
            "selected_by_validation": name == selected,
            "test_used_for_selection": False,
        })
    pd.DataFrame(comparison_rows).to_csv(output_dir / "comparison.csv", index=False)
    readme = [
        "# Delay experiment", "", "Selection used TRAIN to fit and VALIDATION project-level MAE/RMSE/R² to compare candidates.",
        "TEST was not used to tune candidates; only the frozen selected candidate is evaluated after selection.",
        f"Selected candidate: {selected}", f"Decision: {decision['selection_status']}",
        f"Final TEST MAE: {selected_test_metrics['mae']:.4f} days; RMSE {selected_test_metrics['rmse']:.4f}; R² {selected_test_metrics['r2']:.4f}.",
        "The experiment never overwrites artifacts/0.9.0-academic/delay_days.joblib.",
    ]
    (output_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    try:
        report = run_delay_experiment(ROOT / "data/processed/mendeley_core.csv", ROOT / "artifacts/0.9.0-academic")
        print(report["decision"]["selection_status"])
        print(report["test_evaluation_after_freeze"])
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"Delay experiment failed: {error}", file=sys.stderr)
        raise SystemExit(1)