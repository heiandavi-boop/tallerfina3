import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from experiment_delay import _spi_evm_rule, select_delay_candidate
from prunin_ai.training.core import _build_baseline_reports


def test_delay_candidate_selection_uses_validation_metrics_only():
    validation = {
        "lightgbm_current": {"mae": 20.0, "rmse": 28.0, "r2": 0.1},
        "hist_gradient_boosting": {"mae": 18.0, "rmse": 29.0, "r2": 0.2},
        "test_metrics_that_must_not_be_read": {"mae": -1000, "rmse": 0},
    }

    result = select_delay_candidate(validation)

    assert result["selected_candidate"] == "hist_gradient_boosting"
    assert "validation" in result["selection_metric"]
    assert "test" not in result["selection_metric"].lower()


def test_delay_selector_keeps_current_when_candidate_rmse_worsens_too_much():
    validation = {
        "lightgbm_current": {"mae": 20.0, "rmse": 28.0},
        "candidate": {"mae": 19.0, "rmse": 40.0},
    }

    result = select_delay_candidate(validation, rmse_guard_ratio=1.10)

    assert result["selected_candidate"] == "lightgbm_current"
    assert result["selection_status"] == "No candidate exceeded the current model under validation criteria."


def test_median_baselines_fit_only_train_projects_and_report_units():
    train = pd.DataFrame({
        "project_id": ["a", "a", "b", "b"], "snapshot_index": [1, 2, 1, 2],
        "health": ["healthy", "healthy", "critical", "critical"],
        "delay_days": [10.0, 20.0, 30.0, 40.0],
        "cost_overrun_ratio": [0.1, 0.2, 0.3, 0.4],
    })
    validation = pd.DataFrame({
        "project_id": ["c", "c", "d", "d"], "snapshot_index": [1, 2, 1, 2],
        "health": ["healthy", "healthy", "critical", "critical"],
        "delay_days": [15.0, 25.0, 20.0, 30.0],
        "cost_overrun_ratio": [0.15, 0.25, 0.20, 0.30],
    })
    test = pd.DataFrame({
        "project_id": ["d", "e"], "snapshot_index": [1, 1], "health": ["critical", "healthy"],
        "delay_days": [1000.0, 1020.0], "cost_overrun_ratio": [99.0, 101.0],
    })

    baselines, comparison = _build_baseline_reports(
        {"train": train, "validation": validation, "test": test},
        {"health": {"project_level_metrics": {"test": {"macro_f1": 0.3}}},
         "delay_days": {"project_level_metrics": {"test": {"mae": 1.0}}},
         "cost_overrun_ratio": {"project_level_metrics": {"test": {"mae": 0.01}}}},
    )

    assert baselines["delay_days"]["train_statistic"] == 30.0
    assert baselines["cost_overrun_ratio"]["train_statistic"] == pytest.approx(0.3)
    assert baselines["delay_days"]["test"]["project_level_metrics"]["mae"] == 980.0
    assert baselines["cost_overrun_ratio"]["test"]["project_level_metrics"]["mae_percentage_points"] == pytest.approx(9970.0)
    assert set(comparison["baseline_fit_split"]) == {"train only"}


def test_spi_rule_is_deterministic_nonnegative_and_uses_snapshot_features():
    frame = pd.DataFrame({
        "planned_duration_weeks": [10.0, 10.0],
        "true_progress": [0.5, 0.5],
        "spi": [0.5, 1.5],
    })

    result = _spi_evm_rule(frame)

    assert result[0] == 35.0
    assert result[1] == 0.0
    assert (result >= 0).all()