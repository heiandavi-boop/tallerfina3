#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then ./scripts/setup_playground.sh; fi
./scripts/preflight_demo.sh
printf '\nAbriendo PRUNIN AI Core en http://localhost:8000\n'
(sleep 2; open http://localhost:8000 >/dev/null 2>&1 || true) &
./scripts/run_playground.sh
