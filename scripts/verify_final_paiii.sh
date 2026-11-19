#!/usr/bin/env bash
# Final PAIII verification on the student's own machine.
# This does not certify oral performance, user productivity or live deployment.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"

echo "[1/7] Scientific evidence and rubric consistency"
python scripts/check_paiii_delivery_evidence.py
python scripts/validate_original_promise.py --check

echo "[2/7] Python dependency integrity"
python -m pip check

echo "[3/7] Python syntax"
python -m compileall -q src scripts tests

echo "[4/7] Backend regression tests"
python -m pytest -q

echo "[5/7] Frontend tests"
npm test --prefix frontend -- --reporter=dot

echo "[6/7] Frontend build"
npm run build --prefix frontend

echo "[7/7] Academic-artifact preflight (NOT demo fallback)"
if [[ ! -f artifacts/0.9.0-academic/health.joblib || ! -f artifacts/0.9.0-academic/delay_days.joblib || ! -f artifacts/0.9.0-academic/cost_overrun_ratio.joblib ]]; then
  echo "FAIL: missing 0.9.0-academic .joblib files; do not present demo artifacts as academic validation" >&2
  exit 2
fi
export PRUNIN_ARTIFACT_DIR="$(pwd)/artifacts/0.9.0-academic"
bash scripts/preflight_demo.sh

echo "PASS: local technical checks completed. CI for the final SHA, live demo, and oral rubric still require separate evidence."
