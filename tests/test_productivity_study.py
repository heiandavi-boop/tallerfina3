"""Productivity study instrument: assignment balance, validation and honest NO MEDIDA status."""
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import productivity_study as study  # noqa: E402

CASES = [{"case_id": f"C{i}", "difficulty": d} for i, d in enumerate([1, 3, 2, 4])]


def _row(pid, condition, order, seconds, quality=4.0, consent="yes"):
    row = {"participant_id": pid, "case_id": f"{pid}-{condition}", "condition": condition, "order": order,
           "time_seconds": seconds, "consent": consent}
    row.update({field: quality for field in study.QUALITY_FIELDS})
    return row


def test_time_improvement_formula():
    assert study.time_improvement_pct(600, 450) == pytest.approx(25.0)
    with pytest.raises(ValueError):
        study.time_improvement_pct(0, 10)


def test_assignment_counterbalances_order_and_case_condition_mapping():
    plan = study.assign([f"P{i}" for i in range(8)], CASES)
    firsts = Counter(row["condition"] for row in plan if row["order"] == 1)
    assert firsts["manual"] == firsts["prunin"] == 4
    mapping = Counter((row["case_id"], row["condition"]) for row in plan)
    assert mapping[("C0", "manual")] == mapping[("C0", "prunin")]
    pairs = study.pair_cases_by_difficulty(CASES)
    assert pairs == [("C0", "C2"), ("C1", "C3")]


def test_no_real_participants_is_reported_as_not_measured():
    summary = study.analyze([])
    assert summary["status"] == "NO MEDIDA" and summary["reason"] == "insufficient_real_participants"
    assert "time_improvement_pct_of_medians" not in summary


def test_rows_without_consent_or_out_of_range_scores_are_rejected():
    with pytest.raises(ValueError, match="consent"):
        study.validate_rows([_row("P1", "manual", 1, 300, consent="no")])
    with pytest.raises(ValueError, match="0-5"):
        study.validate_rows([_row("P1", "manual", 1, 300, quality=7)])


def test_faster_but_worse_assisted_analysis_does_not_support_productivity_claim():
    rows = []
    for index in range(6):
        pid = f"P{index}"
        rows += [_row(pid, "manual", 1 + index % 2, 600 + index * 10, quality=4.5),
                 _row(pid, "prunin", 2 - index % 2, 300 + index * 7, quality=3.0)]
    summary = study.analyze(rows)
    assert summary["status"] == "MEDIDA"
    assert summary["time_improvement_pct_of_medians"] > 40
    assert summary["quality_delta_mean"] == pytest.approx(-1.5)
    assert summary["productivity_claim_supported"] is False
    assert set(summary["order_effect_time_improvement_pct"]) == {"manual_first", "prunin_first"}
