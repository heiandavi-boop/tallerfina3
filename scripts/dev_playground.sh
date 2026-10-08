#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
python -m uvicorn prunin_ai.api.app:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT
(cd frontend && VITE_API_URL=http://localhost:8000 npm run dev)
