#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ ! -d .venv ]; then "$PYTHON_BIN" -m venv .venv; fi
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if command -v npm >/dev/null 2>&1; then
  echo "Node detectado. El frontend precompilado ya está incluido; no es obligatorio reconstruirlo."
else
  echo "Node no está instalado. No hay problema: se usará frontend/dist precompilado."
fi
echo
echo "Playground preparado. Ejecuta: ./scripts/run_playground.sh"
