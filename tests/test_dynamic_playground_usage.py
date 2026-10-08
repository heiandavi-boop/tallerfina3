import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prunin_ai.api.model_runtime import classify_field_usage, unused_what_if_changes


def test_fields_are_classified_from_manifest_and_team_health_weights():
    catalog = [
        {"name": "spi"},
        {"name": "team_utilization"},
        {"name": "team_stability"},
        {"name": "sector"},
    ]

    fields = classify_field_usage(
        catalog,
        {"spi", "team_utilization"},
        {"team_utilization", "team_stability"},
    )
    result = {field["name"]: field for field in fields}

    assert result["spi"]["usage"] == "ml_feature"
    assert result["spi"]["affects_ml_prediction"] is True
    assert result["spi"]["affects_team_health"] is False
    assert result["team_utilization"]["usage"] == "ml_feature"
    assert result["team_utilization"]["affects_ml_prediction"] is True
    assert result["team_utilization"]["affects_team_health"] is True
    assert result["team_stability"]["usage"] == "team_health"
    assert result["team_stability"]["trained"] is False
    assert result["sector"]["usage"] == "not_used"
    assert result["sector"]["usage_label"] == "No utilizada por este modelo"


def test_what_if_change_filter_allows_ml_and_team_health_only():
    baseline = {"spi": 1.0, "team_stability": 0.8, "sector": "technology"}
    scenario = {"spi": 0.7, "team_stability": 0.5, "sector": "banking"}
    usage = {"spi": "ml_feature", "team_stability": "team_health", "sector": "not_used"}

    assert unused_what_if_changes(baseline, scenario, usage) == ["sector"]


def test_what_if_accepts_unchanged_not_used_values():
    values = {"sector": "technology"}

    assert unused_what_if_changes(values, values.copy(), {"sector": "not_used"}) == []