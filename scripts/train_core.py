from pathlib import Path
import argparse, json, sys
import hashlib
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
from prunin_ai.config import load_config
from prunin_ai.data.local_input import require_local_training_input
from prunin_ai.training.core import train_core

ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True)
ap.add_argument("--version", default="0.9.0-academic")
ap.add_argument("--config", default=str(ROOT / "configs/training.yaml"))
args = ap.parse_args()

try:
	input_path = require_local_training_input(args.input, ROOT)
except (FileNotFoundError, ValueError) as error:
	ap.error(str(error))

split_manifest = None
if args.version == "0.9.0-academic":
	from download_datasets import validate_local_datasets

	try:
		validate_local_datasets()
	except (OSError, ValueError, RuntimeError) as error:
		ap.error(f"TRAINING BLOCKED: Mendeley raw validation failed: {error}")
	readiness_path = ROOT / "artifacts/data_readiness.json"
	if not readiness_path.is_file():
		ap.error("TRAINING BLOCKED: artifacts/data_readiness.json is missing.")
	readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
	if not readiness.get("ready_for_training") or readiness.get("blocking_errors"):
		ap.error("TRAINING BLOCKED: dataset did not pass readiness checks.")
	if readiness.get("leakage_check", {}).get("status") != "passed":
		ap.error("TRAINING BLOCKED: project leakage verification is not PASS.")
	if hashlib.sha256(input_path.read_bytes()).hexdigest() != readiness.get("processed_sha256"):
		ap.error("TRAINING BLOCKED: processed dataset changed after readiness checks.")
	if "mendeley_core.csv" != input_path.name:
		ap.error("Academic artifacts must be trained only from prepared Mendeley.")
	split_path = ROOT / "artifacts" / args.version / "split_manifest.json"
	if not split_path.is_file():
		ap.error("TRAINING BLOCKED: verified split manifest is missing.")
	split_manifest = json.loads(split_path.read_text(encoding="utf-8"))

df = pd.read_csv(input_path, low_memory=False)
cfg = load_config(args.config)
out = ROOT / "artifacts" / args.version
result = train_core(df, cfg, out, split_manifest=split_manifest)
if args.version == "0.9.0-academic":
	(out / "data_readiness.json").write_text(
		json.dumps(readiness, indent=2, ensure_ascii=False), encoding="utf-8"
	)
print(json.dumps(result, indent=2, ensure_ascii=False))
print(f"Artefactos: {out}")
