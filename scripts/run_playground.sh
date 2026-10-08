#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
export PRUNIN_ARTIFACT_DIR="${PRUNIN_ARTIFACT_DIR:-artifacts/0.9.0-academic}"
PORT="${PORT:-8000}"
if [ ! -s "$PRUNIN_ARTIFACT_DIR/health.joblib" ]; then
  echo "Academic artifacts unavailable: $PRUNIN_ARTIFACT_DIR" >&2
  exit 1
fi
echo "PRUNIN AI Core Playground"
echo "Local:   http://localhost:${PORT}"
LAN_IP=""
if command -v ipconfig >/dev/null 2>&1; then
  LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
fi
if [ -z "$LAN_IP" ] && command -v hostname >/dev/null 2>&1; then
  LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
fi
if [ -n "$LAN_IP" ]; then
  echo "Red LAN: http://${LAN_IP}:${PORT}  (para celulares en la misma red)"
fi
if [ -n "${PRUNIN_PUBLIC_URL:-}" ]; then
  echo "Pública:  ${PRUNIN_PUBLIC_URL}"
fi
exec python -m uvicorn prunin_ai.api.app:app --host "${HOST:-0.0.0.0}" --port "$PORT"
