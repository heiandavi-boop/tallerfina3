from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prunin_ai.config import load_config
from prunin_ai.features.team_health import compute_team_health


def test_team_health_good_team():
    cfg = load_config(ROOT / "configs/training.yaml")["team_health"]
    r = compute_team_health({
        "team_utilization": .82, "team_capacity_ratio": 1.0, "average_productivity": .95,
        "rework_ratio": .03, "defect_rate": .02, "team_stability": .9, "collaboration_level": .85,
    }, cfg)
    assert r.score is not None and r.score > .75
    assert r.level == "healthy"


def test_team_health_requires_evidence():
    cfg = load_config(ROOT / "configs/training.yaml")["team_health"]
    r = compute_team_health({"team_utilization": .8}, cfg)
    assert r.score is None
    assert r.level == "insufficient_data"
