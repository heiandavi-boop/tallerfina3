from pathlib import Path
import argparse, json, sys, warnings
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
from prunin_ai.config import load_config
from prunin_ai.inference.brain import PruninAcademicBrain

ap = argparse.ArgumentParser()
ap.add_argument("--artifact", required=True)
ap.add_argument("--input", required=True)
args = ap.parse_args()
warnings.filterwarnings("ignore", category=UserWarning, module=r"sklearn\.utils\.validation")
df = pd.read_csv(args.input, low_memory=False)
row = df.iloc[-1].to_dict()
brain = PruninAcademicBrain(args.artifact, load_config(ROOT / "configs/training.yaml"))
print(json.dumps(brain.predict(row), indent=2, ensure_ascii=False, default=str))
