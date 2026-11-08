import importlib.util
import json
from pathlib import Path
import sys

import pandas as pd

from prunin_ai.monitoring.drift import (
    assess_input_ood,
    build_reference_profile,
    compare_feature_distributions,
)


ROOT = Path(__file__).resolve().parents[1]


def test_reference_profile_uses_train_projects_only(tmp_path):
    script_path = ROOT / "scripts/check_drift.py"
    spec = importlib.util.spec_from_file_location("check_drift", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    artifact = tmp_path / "0.9.0-academic"
    artifact.mkdir()
    (artifact / "feature_manifest.json").write_text(json.dumps({
        "numeric_features": ["spi"], "categorical_features": ["project_type"]
    }))
    (artifact / "split_manifest.json").write_text(json.dumps({
        "train": ["train-1"], "validation": ["valid-1"], "test": ["test-1"]
    }))
    data = tmp_path / "projects.csv"
    pd.DataFrame({
        "project_id": ["train-1", "valid-1", "test-1"],
        "spi": [1.0, 20.0, 200.0],
        "project_type": ["it", "healthcare", "construction"],
    }).to_csv(data, index=False)

    reference, profile = module.build_train_reference(artifact, data)

    assert reference["project_id"].tolist() == ["train-1"]
    assert profile["reference_project_count"] == 1
    assert profile["numeric"]["spi"]["median"] == 1.0
    assert profile["categorical"]["project_type"]["categories"] == ["it"]


def test_input_ood_flags_numeric_extreme_and_unseen_category_only():
    reference = pd.DataFrame({"spi": [0.8, 0.9, 1.0, 1.1, 1.2], "kind": ["it", "it", "build", "it", "build"]})
    profile = build_reference_profile(reference, ["spi"], ["kind"])

    result = assess_input_ood({"spi": 10.0, "kind": "unknown"}, profile)

    assert result["ood_warning"] is True
    assert result["ood_features"] == ["kind", "spi"]
    assert result["ood_details"]["spi"]["kind"] == "outside_training_iqr_fence"


def test_input_ood_does_not_warn_for_reference_values_or_missing_features():
    reference = pd.DataFrame({"spi": [0.8, 0.9, 1.0, 1.1, 1.2], "kind": ["it", "it", "build", "it", "build"]})
    profile = build_reference_profile(reference, ["spi"], ["kind"])

    result = assess_input_ood({"spi": 1.0, "kind": "it"}, profile)

    assert result == {"ood_warning": False, "ood_features": [], "ood_details": {}}


def test_batch_drift_reports_psi_and_missing_rate_shift():
    reference = pd.DataFrame({"spi": [0.8, 0.9, 1.0, 1.1, 1.2], "kind": ["it", "it", "build", "it", "build"]})
    current = pd.DataFrame({"spi": [2.0, 2.1, 2.2, None, None], "kind": ["unknown", "unknown", None, "unknown", "unknown"]})
    profile = build_reference_profile(reference, ["spi"], ["kind"])

    result = compare_feature_distributions(reference, current, profile)

    assert result["status"] == "complete"
    assert result["alert"] is True
    assert {"spi", "kind"} <= set(result["alert_features"])
    assert result["features"]["spi"]["missing_rate_shift"] == 0.4
    assert "does not change model predictions" in result["interpretation"]


def test_empty_cohorts_are_rejected():
    reference = pd.DataFrame({"spi": [1.0]})
    profile = build_reference_profile(reference, ["spi"], [])

    try:
        compare_feature_distributions(reference, reference.iloc[0:0], profile)
    except ValueError as exc:
        assert "contener filas" in str(exc)
    else:
        raise AssertionError("Empty drift cohort should be rejected")