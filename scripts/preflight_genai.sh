#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
python scripts/test_ollama_integration.py "$@"