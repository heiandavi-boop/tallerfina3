from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prunin_ai.data.demo import generate_demo
from prunin_ai.training.core import _split_groups


def test_group_split_no_project_leakage():
    df = generate_demo(projects=60, snapshots=3, seed=7)
    a,b,c = _split_groups(df, 42)
    sets = [set(df.iloc[x].project_id) for x in (a,b,c)]
    assert not (sets[0] & sets[1])
    assert not (sets[0] & sets[2])
    assert not (sets[1] & sets[2])
