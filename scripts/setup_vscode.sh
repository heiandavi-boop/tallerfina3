#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
printf '\nPRUNIN AI Core listo.\n'
printf '1) En VS Code: Command Palette > Python: Select Interpreter > .venv/bin/python\n'
printf '2) Ejecuta: python scripts/bootstrap_demo_data.py\n'
printf '3) Ejecuta: python scripts/train_core.py --input data/processed/demo_core.csv --version demo-0.1.0\n'
