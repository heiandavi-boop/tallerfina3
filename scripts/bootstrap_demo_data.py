from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prunin_ai.config import load_config
from prunin_ai.data.demo import generate_demo
from prunin_ai.features.team_health import compute_team_health
from prunin_ai.targets import add_targets

cfg = load_config(ROOT / "configs/training.yaml")
df = generate_demo()
team = df.apply(lambda r: compute_team_health(r.to_dict(), cfg["team_health"]).score, axis=1)
df["team_health_index"] = team
df = add_targets(df, cfg["target_rules"])
out = ROOT / "data/processed/demo_core.csv"
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
print(f"OK: {out} | rows={len(df)} | projects={df.project_id.nunique()}")
print(df[["health","final_status"]].value_counts().head(12))
