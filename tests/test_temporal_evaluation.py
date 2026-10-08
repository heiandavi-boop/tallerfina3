import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_temporal import select_snapshot_at_cutoff, select_test_project_snapshots


def test_cutoff_selects_closest_snapshot_without_future_progress():
    snapshots = pd.DataFrame({
        "project_id": ["mendeley::A"] * 4,
        "snapshot_index": [1, 2, 3, 4],
        "true_progress": [0.12, 0.22, 0.39, 0.61],
    })

    selected = select_snapshot_at_cutoff(snapshots, 0.40)

    assert selected["snapshot_index"] == 3
    assert selected["true_progress"] == pytest.approx(0.39)
    assert selected["true_progress"] <= 0.40


def test_temporal_evaluation_uses_test_only_and_one_snapshot_per_project():
    data = pd.DataFrame({
        "project_id": ["train::A", "test::B", "test::B", "test::C"],
        "snapshot_index": [1, 1, 2, 1],
        "true_progress": [0.19, 0.10, 0.38, 0.70],
    })

    selected, excluded = select_test_project_snapshots(data, {"test::B", "test::C"}, 0.40)

    assert selected["project_id"].tolist() == ["test::B"]
    assert selected["snapshot_index"].tolist() == [2]
    assert excluded == 1
    assert selected["project_id"].nunique() == len(selected)
    assert (selected["true_progress"] <= 0.40).all()


def test_cutoff_with_no_eligible_snapshot_returns_none():
    snapshots = pd.DataFrame({"project_id": ["p"], "true_progress": [0.35]})

    assert select_snapshot_at_cutoff(snapshots, 0.20) is None


def test_invalid_cutoff_is_rejected():
    with pytest.raises(ValueError, match="cutoff"):
        select_snapshot_at_cutoff(pd.DataFrame({"true_progress": [0.1]}), 0.0)