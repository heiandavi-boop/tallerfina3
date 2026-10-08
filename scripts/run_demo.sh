#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -n "${PYTHON_BIN:-}" ]]; then
  PY="$PYTHON_BIN"
elif [[ -x ".venv/bin/python" ]]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi
"$PY" scripts/bootstrap_demo_data.py
"$PY" scripts/audit_dataset.py --input data/processed/demo_core.csv --output artifacts/demo-audit.json
"$PY" scripts/train_core.py --input data/processed/demo_core.csv --version demo-0.1.0
PYTHONWARNINGS="ignore:X does not have valid feature names:UserWarning" "$PY" scripts/predict_example.py --artifact artifacts/demo-0.1.0 --input data/processed/demo_core.csv
