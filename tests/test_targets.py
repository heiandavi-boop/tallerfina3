from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
from prunin_ai.config import load_config
from prunin_ai.targets import add_targets


def test_target_rules():
    cfg = load_config(ROOT / "configs/training.yaml")
    df = pd.DataFrame({
        "planned_duration_days": [100,100,100],
        "delay_days": [2,10,30],
        "cost_overrun_ratio": [.01,.10,.35],
    })
    out = add_targets(df, cfg["target_rules"])
    assert out.health.tolist() == ["healthy","at_risk","critical"]
    assert out.final_status.tolist() == ["successful","challenged","critical"]
