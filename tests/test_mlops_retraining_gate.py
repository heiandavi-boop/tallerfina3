"""MLOps policy refuses inferred retraining on demo or unlabeled data."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mlops_gate", ROOT / "scripts/mlops_retraining_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def report(**overrides):
    value = {
        "status": "complete",
        "alert": True,
        "artifact_version": "0.9.0-academic",
        "input_hashes": {"current_batch_sha256": "new123", "reference_dataset_sha256": "old456"},
    }
    value.update(overrides)
    return value


def labels(**overrides):
    value = {"approved": True, "outcomes_verified": True, "batch_sha256": "new123", "project_count": 60}
    value.update(overrides)
    return value


def test_demo_never_eligible():
    result = gate.decide(report(artifact_version="demo-0.1.0"), labels(), True)
    assert result["status"] == "BLOCKED"
    assert "demo_artifact_not_eligible" in result["blockers"]


def test_unlabeled_or_unapproved_never_eligible():
    assert gate.decide(report(), None, True)["status"] == "BLOCKED"
    assert gate.decide(report(), labels(), False)["status"] == "BLOCKED"
    assert gate.decide(report(), labels(batch_sha256="wrong"), True)["status"] == "BLOCKED"


def test_no_drift_or_no_new_batch_blocks():
    assert gate.decide(report(alert=False), labels(), True)["status"] == "BLOCKED"
    same = report(input_hashes={"current_batch_sha256": "x", "reference_dataset_sha256": "x"})
    assert gate.decide(same, labels(batch_sha256="x"), True)["status"] == "BLOCKED"


def test_gate_only_allows_evaluation_never_trains_or_promotes():
    decision = gate.decide(report(), labels(), True)
    assert decision["status"] == "ELIGIBLE_FOR_CANDIDATE_TRAINING"
    assert decision["retraining_executed"] is False
    assert decision["promotion_executed"] is False
