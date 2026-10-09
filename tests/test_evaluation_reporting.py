import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from export_report import export_report
from generate_evaluation_plots import generate_plots
from prunin_ai.inference.brain import PruninAcademicBrain, derive_final_status
from prunin_ai.training.core import (
    _classification_metrics, _feature_importance, _model_tasks,
    _project_latest_snapshots, _regression_metrics,
)
from prunin_ai.training.reproducibility import build_reproducibility


def test_classification_metrics_include_class_support_and_confusion_matrix():
    result = _classification_metrics(
        ["healthy", "healthy", "at_risk", "critical"],
        ["healthy", "at_risk", "at_risk", "at_risk"],
        ["healthy", "at_risk", "critical"],
    )

    assert result["labels"] == ["healthy", "at_risk", "critical"]
    assert result["confusion_matrix"] == [[1, 1, 0], [0, 1, 0], [0, 1, 0]]
    assert result["per_class"]["critical"]["support"] == 1
    assert result["per_class"]["critical"]["recall"] == 0
    assert "weighted_f1" in result and "precision_macro" in result and "recall_weighted" in result


def test_regression_metrics_keep_negative_r2_and_skip_unsafe_mape():
    result = _regression_metrics([0.0, 1.0, -1.0], [2.0, 0.0, 1.0])

    assert result["r2"] < 0
    assert result["mape_percent"] is None
    assert "zero or negative" in result["mape_status"]
    assert set(result["absolute_error_percentiles"]) == {"p50", "p75", "p90", "p95"}


def test_lightgbm_native_feature_importance_exports_gain_and_split(tmp_path):
    class FakeBooster:
        @staticmethod
        def feature_importance(importance_type):
            return [20, 5] if importance_type == "gain" else [4, 2]

    estimator = SimpleNamespace(booster_=FakeBooster())
    prep = SimpleNamespace(get_feature_names_out=lambda: ["num__spi", "cat__methodology_agile"])
    pipe = SimpleNamespace(named_steps={"model": estimator, "prep": prep})

    _feature_importance(pipe, tmp_path, "health")
    result = pd.read_csv(tmp_path / "feature_importance_health.csv")

    assert result["raw_feature"].tolist() == ["num__spi", "cat__methodology_agile"]
    assert result["display_feature"].tolist() == ["spi", "methodology = agile"]
    assert result["gain"].tolist() == [20, 5]
    assert result["split"].tolist() == [4, 2]


def _artifact_fixture(tmp_path):
    artifact = tmp_path / "artifacts/0.9.0-academic"
    artifact.mkdir(parents=True)
    health = _classification_metrics(
        ["healthy", "at_risk"], ["healthy", "healthy"], ["healthy", "at_risk", "critical"]
    )
    regression = _regression_metrics([1.0, 2.0], [1.2, 2.4])
    metrics = {
        "health": {"status": "trained", "validation": health, "test": health,
                   "row_level_metrics": {"validation": health, "test": health},
                   "project_level_metrics": {
                       "validation": {**health, "confusion_matrix": [[0, 1, 0], [0, 1, 0], [0, 0, 0]]},
                       "test": {**health, "confusion_matrix": [[0, 1, 0], [0, 1, 0], [0, 0, 0]]},
                       "validation_project_count": 1, "test_project_count": 1,
                   },
                   "train_rows": 4, "validation_rows": 2, "test_rows": 2},
        "delay_days": {"status": "trained", "validation": regression, "test": regression},
        "cost_overrun_ratio": {"status": "trained", "validation": regression, "test": {**regression, "mae_percentage_points": regression["mae"] * 100}},
        "final_status": {"status": "derived", "source": "health", "mapping": {"healthy": "successful", "at_risk": "challenged", "critical": "critical"}},
    }
    manifest = {
        "final_status_mode": "derived_from_health", "dataset_source": "Mendeley Data",
        "dataset_type": "synthetic external data", "model_type": "LightGBM",
        "numeric_features": ["spi"], "categorical_features": ["methodology"],
        "target_columns_excluded": ["health", "delay_days", "cost_overrun_ratio"],
    }
    readiness = {
        "project_count": 8, "snapshot_count": 16,
        "health_distribution": {"healthy": 4, "at_risk": 4},
        "final_status_distribution": {"successful": 4, "challenged": 4},
        "target_distribution": {name: {"count": 16} for name in ("health", "final_status", "delay_days", "cost_overrun_ratio")},
        "feature_coverage": {"spi": 1.0, "methodology": 1.0}, "missing_features": [],
        "leakage_risks": ["Risk note"],
        "leakage_check": {"status": "passed"},
    }
    temporal = {"cutoffs": [{
        "cutoff": 0.2, "test_project_count": 1,
        "health": {"macro_f1": 0.5}, "delay_days": {"mae": 4.0},
        "cost_overrun_ratio": {"mae": 0.1},
    }], "selected_project_snapshots": [], "final_status_mode": "derived_from_health"}
    reproducibility = {
        "python_version": "3.12.0", "git_commit_sha": "abc", "random_seed": 42,
        "timestamp_utc": "2026-10-08T00:00:00+00:00", "split_project_counts": {"train": 6, "validation": 1, "test": 1},
    }
    baselines = {
        "health": {"method": "train-only majority", "train_statistic": "healthy",
                   "test": {"project_level_metrics": {"macro_f1": 0.3}},
                   "project_level_test_model": {"macro_f1": 0.5}},
        "delay_days": {"method": "train-only median", "train_statistic": 20.0,
                       "test": {"project_level_metrics": {"mae": 12.0}},
                       "project_level_test_model": {"mae": 10.0}},
        "cost_overrun_ratio": {"method": "train-only median", "train_statistic": 0.0,
                               "test": {"project_level_metrics": {"mae_percentage_points": 5.0}},
                               "project_level_test_model": {"mae_percentage_points": 4.0}},
    }
    values = {
        "metrics.json": metrics, "feature_manifest.json": manifest,
        "data_readiness.json": readiness, "temporal_evaluation.json": temporal,
        "reproducibility.json": reproducibility,
        "split_manifest.json": {"train": ["p1"], "validation": ["p2"], "test": ["p3"]},
        "baselines.json": baselines,
    }
    for name, value in values.items():
        (artifact / name).write_text(json.dumps(value), encoding="utf-8")
    pd.DataFrame({"cutoff": [0.2], "project_id": ["p3"]}).to_csv(artifact / "temporal_evaluation.csv", index=False)
    pd.DataFrame([{"target": "health", "baseline_value": 0.5, "model_value": 0.6}]).to_csv(
        artifact / "baseline_comparison.csv", index=False
    )
    return artifact, metrics, temporal


def test_export_report_creates_lightweight_versionable_evidence(tmp_path):
    artifact, _, _ = _artifact_fixture(tmp_path)
    reports = tmp_path / "reports/0.9.0-academic"

    files = export_report(artifact, reports)

    expected = {
        "metrics.json", "data_readiness.json", "feature_manifest.json", "training_summary.json",
        "experiment_summary.md", "health_confusion_matrix.csv", "health_classification_report.csv",
        "temporal_evaluation.json", "temporal_evaluation.csv", "dataset_summary.json",
        "dataset_summary.md", "split_summary.json", "reproducibility.json", "baselines.json",
        "baseline_comparison.csv",
    }
    assert expected <= {path.name for path in files}
    assert not any(path.suffix in {".joblib", ".parquet", ".zip"} for path in files)
    assert not (reports / "final_status_confusion_matrix.csv").exists()
    reproduced = json.loads((reports / "reproducibility.json").read_text(encoding="utf-8"))
    assert reproduced["experiment_source_commit"] == "abc"
    assert reproduced["report_generation_commit"] == reproduced["repository_head_at_export"]
    project_matrix = pd.read_csv(reports / "health_confusion_matrix.csv", index_col=0)
    snapshot_matrix = pd.read_csv(reports / "health_snapshot_confusion_matrix.csv", index_col=0)
    assert project_matrix.to_numpy().tolist() == [[0, 1, 0], [0, 1, 0], [0, 0, 0]]
    assert snapshot_matrix.to_numpy().tolist() == [[1, 0, 0], [1, 0, 0], [0, 0, 0]]
    dataset_summary = json.loads((reports / "dataset_summary.json").read_text(encoding="utf-8"))
    assert dataset_summary["features_used"] == ["spi", "methodology"]
    baseline_summary = json.loads((reports / "baselines.json").read_text(encoding="utf-8"))
    cost_improvement = baseline_summary["cost_overrun_ratio"]["project_level_test_improvement"]
    assert cost_improvement["unit"] == "percentage points"
    assert cost_improvement["baseline_value"] == 5.0
    assert cost_improvement["model_value"] == 4.0
    assert cost_improvement["model_minus_baseline"] == 1.0
    summary_text = (reports / "experiment_summary.md").read_text(encoding="utf-8")
    assert "Project-level evaluation" in summary_text
    assert "Snapshot-level evaluation" in summary_text
    assert '"critical_recall": 0.0' in summary_text


def test_reproducibility_records_versions_hash_seed_and_split_counts(tmp_path):
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "data/raw/dataset_manifest.json").write_text(json.dumps({"files": [
        {"dataset": "mendeley_evm", "local_path": "data/raw/mendeley/a.csv", "sha256": "abc"}
    ]}), encoding="utf-8")

    result = build_reproducibility(tmp_path, "0.9.0-academic", {"random_seed": 7},
                                   {"processed_sha256": "def"}, {"train": [1, 2], "validation": [3], "test": [4]})

    assert result["random_seed"] == 7
    assert result["dataset_sha256"]["processed"] == "def"
    assert result["dataset_sha256"]["raw_mendeley_files"]["data/raw/mendeley/a.csv"] == "abc"
    assert result["split_project_counts"] == {"train": 2, "validation": 1, "test": 1}
    assert set(result["packages"]) == {"pandas", "numpy", "sklearn", "lightgbm"}
    assert result["experiment_source_commit"] is None
    assert result["report_generation_commit"] is None
    assert result["repository_head_at_export"] is None


def test_plot_generation_creates_diagnostic_images(tmp_path):
    artifact, metrics, temporal = _artifact_fixture(tmp_path)
    reports = tmp_path / "reports/0.9.0-academic"
    export_report(artifact, reports)
    (reports / "temporal_evaluation.json").write_text(json.dumps(temporal), encoding="utf-8")
    for name, rows in {
        "health": [{"feature": "spi", "gain": 3, "split": 2}],
        "delay": [{"feature": "spi", "gain": 2, "split": 1}],
        "cost": [{"feature": "spi", "gain": 1, "split": 1}],
    }.items():
        pd.DataFrame(rows).to_csv(reports / f"feature_importance_{name}.csv", index=False)
    pd.DataFrame({
        "actual_delay_days": [1.0], "predicted_delay_days": [1.2],
        "actual_cost_overrun_ratio": [0.1], "predicted_cost_overrun_ratio": [0.2],
    }).to_csv(artifact / "test_project_predictions.csv", index=False)

    generated = generate_plots(artifact, reports)

    names = {path.name for path in generated}
    assert "health_confusion_matrix.png" in names
    assert "health_snapshot_confusion_matrix.png" in names
    assert "delay_actual_vs_predicted.png" in names
    assert "temporal_health_macro_f1.png" in names
    assert "feature_importance_cost.png" in names
    assert "baseline_comparison.png" in names


def test_train_all_stops_before_download_when_environment_gate_fails():
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/train_all.sh")], cwd=ROOT,
        env={**os.environ, "PYTHON_BIN": "/usr/bin/false"},
        capture_output=True, text=True, check=False, timeout=20,
    )

    assert result.returncode != 0
    assert "Mendeley metadata" not in result.stdout
    assert "Academic Pipeline" in result.stdout


def test_final_status_mapping_is_deterministically_derived():
    assert derive_final_status("healthy") == "successful"
    assert derive_final_status("at_risk") == "challenged"
    assert derive_final_status("critical") == "critical"
    assert derive_final_status("unknown") == "incomplete"


def test_mendeley_model_spec_does_not_train_redundant_final_status():
    assert [name for name, _ in _model_tasks("derived_from_health")] == [
        "health", "delay_days", "cost_overrun_ratio"
    ]
    assert "final_status" in [name for name, _ in _model_tasks("independent_model")]


def test_project_level_evaluation_uses_only_latest_snapshot_once():
    frame = pd.DataFrame({
        "project_id": ["p1", "p1", "p2", "p2", "p2"],
        "snapshot_index": [1, 3, 1, 2, 4],
        "value": [10, 30, 5, 15, 40],
    })

    result = _project_latest_snapshots(frame)

    assert result["project_id"].nunique() == len(result) == 2
    assert result.set_index("project_id")["value"].to_dict() == {"p1": 30, "p2": 40}


def test_academic_brain_ignores_stale_final_status_model_but_demo_keeps_it(monkeypatch, tmp_path):
    derived_dir = tmp_path / "academic"
    demo_dir = tmp_path / "demo"
    derived_dir.mkdir()
    demo_dir.mkdir()
    for directory in (derived_dir, demo_dir):
        for model in ("health", "final_status", "delay_days", "cost_overrun_ratio"):
            (directory / f"{model}.joblib").write_bytes(b"model")
    (derived_dir / "feature_manifest.json").write_text(
        json.dumps({"final_status_mode": "derived_from_health"}), encoding="utf-8"
    )
    (demo_dir / "feature_manifest.json").write_text(
        json.dumps({"final_status_mode": "independent_model"}), encoding="utf-8"
    )
    loaded = []
    monkeypatch.setattr("prunin_ai.inference.brain.joblib.load", lambda path: loaded.append(Path(path).name) or object())

    academic = PruninAcademicBrain(derived_dir, {})
    academic_loaded = set(loaded)
    loaded.clear()
    demo = PruninAcademicBrain(demo_dir, {})

    assert "final_status.joblib" not in academic_loaded
    assert "final_status" not in academic.models
    assert "final_status.joblib" in set(loaded)
    assert "final_status" in demo.models