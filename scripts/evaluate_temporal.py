#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prunin_ai.training.core import _classification_metrics, _regression_metrics

CUTOFFS = (0.20, 0.40, 0.60, 0.80)
STATUS_FROM_HEALTH = {"healthy": "successful", "at_risk": "challenged", "critical": "critical"}


def select_snapshot_at_cutoff(project_snapshots: pd.DataFrame, cutoff: float) -> pd.Series | None:
    if not 0 < cutoff <= 1:
        raise ValueError("cutoff must be in (0, 1].")
    eligible = project_snapshots.loc[
        pd.to_numeric(project_snapshots["true_progress"], errors="coerce") <= cutoff
    ]
    if eligible.empty:
        return None
    sort_columns = ["true_progress"]
    if "snapshot_index" in eligible.columns:
        sort_columns.append("snapshot_index")
    return eligible.sort_values(sort_columns, kind="stable").iloc[-1]


def select_test_project_snapshots(
    data: pd.DataFrame,
    test_project_ids: set[str],
    cutoff: float,
) -> tuple[pd.DataFrame, int]:
    test = data.loc[data["project_id"].astype(str).isin(test_project_ids)]
    selected = []
    excluded = 0
    for _, project in test.groupby("project_id", sort=False):
        snapshot = select_snapshot_at_cutoff(project, cutoff)
        if snapshot is None:
            excluded += 1
        else:
            selected.append(snapshot)
    frame = pd.DataFrame(selected).reset_index(drop=True)
    if len(frame) and (pd.to_numeric(frame["true_progress"], errors="coerce") > cutoff).any():
        raise RuntimeError("Future snapshot selected after the requested progress cutoff.")
    if frame["project_id"].duplicated().any():
        raise RuntimeError("Temporal evaluation selected more than one snapshot per project.")
    return frame, excluded


def evaluate_temporal(
    input_path: Path,
    artifact_dir: Path,
    cutoffs: tuple[float, ...] = CUTOFFS,
) -> dict:
    feature_manifest = json.loads((artifact_dir / "feature_manifest.json").read_text(encoding="utf-8"))
    split_manifest = json.loads((artifact_dir / "split_manifest.json").read_text(encoding="utf-8"))
    if feature_manifest.get("final_status_mode") == "independent_model":
        final_status_model = joblib.load(artifact_dir / "final_status.joblib")
    else:
        final_status_model = None
    models = {
        "health": joblib.load(artifact_dir / "health.joblib"),
        "delay_days": joblib.load(artifact_dir / "delay_days.joblib"),
        "cost_overrun_ratio": joblib.load(artifact_dir / "cost_overrun_ratio.joblib"),
    }
    if final_status_model is not None:
        models["final_status"] = final_status_model
    data = pd.read_csv(input_path, low_memory=False)
    test_project_ids = set(map(str, split_manifest["test"]))
    test = data.loc[data["project_id"].astype(str).isin(test_project_ids)].copy()
    features = feature_manifest["numeric_features"] + feature_manifest["categorical_features"]
    missing = [name for name in features if name not in test]
    if missing:
        raise ValueError(f"Temporal evaluation is missing trained features: {missing}")
    results = []
    for cutoff in cutoffs:
        frame, excluded = select_test_project_snapshots(test, test_project_ids, cutoff)
        if len(frame):
            inputs = frame[features]
            health_model = models["health"]
            health_pred = health_model.predict(inputs)
            health_labels = list(health_model.named_steps["model"].classes_)
            health_metrics = _classification_metrics(frame["health"].astype(str), health_pred, health_labels)
            delay_pred = models["delay_days"].predict(inputs)
            cost_pred = models["cost_overrun_ratio"].predict(inputs)
            row = {
                "cutoff": cutoff,
                "test_project_count": int(frame["project_id"].nunique()),
                "excluded_test_project_count": excluded,
                "selected_snapshot_count": int(len(frame)),
                "max_selected_progress": float(frame["true_progress"].max()),
                "health": health_metrics,
                "delay_days": _regression_metrics(frame["delay_days"], delay_pred),
                "cost_overrun_ratio": _regression_metrics(frame["cost_overrun_ratio"], cost_pred),
                "row_level_metrics": {
                    "status": "not separately aggregated; exactly one selected observation per test project",
                    "observation_count": int(len(frame)),
                },
                "project_level_metrics": {
                    "status": "computed; one selected snapshot per test project",
                    "project_count": int(frame["project_id"].nunique()),
                },
            }
            if final_status_model is not None:
                row["final_status"] = _classification_metrics(
                    frame["final_status"].astype(str), final_status_model.predict(inputs),
                    list(final_status_model.named_steps["model"].classes_),
                )
            else:
                row["final_status"] = {
                    "status": "derived_from_health",
                    "mapping": STATUS_FROM_HEALTH,
                    "project_count": int(len(frame)),
                }
        else:
            row = {
                "cutoff": cutoff,
                "test_project_count": 0,
                "excluded_test_project_count": excluded,
                "selected_snapshot_count": 0,
                "max_selected_progress": None,
                "health": None,
                "final_status": {"status": "derived_from_health"} if final_status_model is None else None,
                "delay_days": None,
                "cost_overrun_ratio": None,
                "row_level_metrics": {"status": "no eligible observations", "observation_count": 0},
                "project_level_metrics": {"status": "no eligible projects", "project_count": 0},
            }
        results.append(row)

    return {
        "dataset_source": "Mendeley Data 2p5sz57wh2 version 2",
        "evaluation_split": "test only; project IDs loaded from split_manifest.json",
        "selection_rule": "For each test project, select the maximum true_progress <= cutoff; ties select the latest snapshot_index.",
        "cutoffs": results,
        "final_status_mode": feature_manifest.get("final_status_mode", "independent_model"),
    }


def write_temporal_reports(result: dict, artifact_dir: Path) -> None:
    json_path = artifact_dir / "temporal_evaluation.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    rows = []
    for cutoff in result["cutoffs"]:
        health = cutoff.get("health") or {}
        delay = cutoff.get("delay_days") or {}
        cost = cutoff.get("cost_overrun_ratio") or {}
        row = {
            "cutoff_percent": cutoff["cutoff"] * 100,
            "test_project_count": cutoff.get("test_project_count", 0),
            "excluded_test_project_count": cutoff.get("excluded_test_project_count", 0),
            "max_selected_progress": cutoff.get("max_selected_progress"),
            "health_balanced_accuracy": health.get("balanced_accuracy"),
            "health_macro_f1": health.get("macro_f1"),
            "health_weighted_f1": health.get("weighted_f1"),
            "delay_mae_days": delay.get("mae"),
            "delay_rmse_days": delay.get("rmse"),
            "delay_r2": delay.get("r2"),
            "cost_mae_ratio": cost.get("mae"),
            "cost_mae_percentage_points": cost.get("mae_percentage_points"),
            "cost_rmse_ratio": cost.get("rmse"),
            "cost_r2": cost.get("r2"),
            "final_status_mode": result.get("final_status_mode"),
        }
        for label, class_metrics in health.get("per_class", {}).items():
            row[f"health_recall_{label}"] = class_metrics.get("recall")
        rows.append(row)
    pd.DataFrame(rows).to_csv(artifact_dir / "temporal_evaluation.csv", index=False)


if __name__ == "__main__":
    artifact_dir = ROOT / "artifacts/0.9.0-academic"
    try:
        report = evaluate_temporal(ROOT / "data/processed/mendeley_core.csv", artifact_dir)
        write_temporal_reports(report, artifact_dir)
        for result in report["cutoffs"]:
            health_macro = result["health"]["macro_f1"] if result["health"] else None
            delay_mae = result["delay_days"]["mae"] if result["delay_days"] else None
            cost_mae = result["cost_overrun_ratio"]["mae"] if result["cost_overrun_ratio"] else None
            print(
                f"{result['cutoff']:.0%}: n={result['test_project_count']} "
                f"health_macro_f1={health_macro} delay_mae={delay_mae} cost_mae={cost_mae}"
            )
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"Temporal evaluation failed: {error}", file=sys.stderr)
        raise SystemExit(1)