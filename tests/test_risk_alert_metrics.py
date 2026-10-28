import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_original_promise import build_result, risk_alert_metrics


def test_risk_alert_aggregates_at_risk_and_critical():
    labels = ["at_risk", "critical", "healthy"]
    cm = [
        [317, 35, 77],
        [13, 25, 6],
        [28, 5, 94],
    ]
    result = risk_alert_metrics(cm, labels)

    assert result["tp"] == 390
    assert result["fn"] == 83
    assert result["fp"] == 33
    assert result["tn"] == 94
    assert result["recall"] == pytest.approx(390 / 473)
    assert result["precision"] == pytest.approx(390 / 423)


def test_original_promise_crosses_full_cohort_target_at_60_percent():
    result = build_result()
    first = result["first_precompletion_cutoff_reaching_target"]

    assert first["cutoff_percent"] == 60
    assert first["full_cohort_detection_rate"] == pytest.approx(359 / 473)
    assert first["project_coverage"] == pytest.approx(0.96)
    assert result["final"]["risk_alert_recall"] == pytest.approx(390 / 473)
    assert result["final"]["exact_critical_recall"] == pytest.approx(25 / 44)
