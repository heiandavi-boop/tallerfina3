#!/usr/bin/env bash
# A local/CI acceptance check. Uses demo-only artifacts, never academic model files.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo "Docker is required"; exit 1; }
command -v curl >/dev/null || { echo "curl is required"; exit 1; }

image="${PRUNIN_SMOKE_IMAGE:-prunin-ai-core:rubric-smoke}"
port="${PRUNIN_SMOKE_PORT:-18765}"
docker build --file Dockerfile.playground --tag "$image" .
cid="$(docker run -d --publish "127.0.0.1:${port}:8000" --env PRUNIN_ARTIFACT_DIR=artifacts/demo-0.1.0 "$image")"
cleanup() { docker rm -f "$cid" >/dev/null 2>&1 || true; }
trap cleanup EXIT

ready=0
for attempt in $(seq 1 50); do
  if curl --fail --silent --show-error --max-time 2 "http://127.0.0.1:${port}/api/ready" > /tmp/prunin-ready.json 2>/dev/null; then
    ready=1
    break
  fi
  if [ "$(docker inspect -f '{{.State.Running}}' "$cid" 2>/dev/null || echo false)" != "true" ]; then
    echo "Container exited before readiness; diagnostic logs:"
    docker logs "$cid" --tail 100 || true
    docker inspect -f 'Exit code: {{.State.ExitCode}} / status: {{.State.Status}}' "$cid" || true
    exit 1
  fi
  sleep 2
done
if [ "$ready" != 1 ]; then
  echo "Container did not become ready. Logs:"
  docker logs "$cid" --tail 80 || true
  exit 1
fi
python3 - <<'PY'
import json
from pathlib import Path
r = json.loads(Path("/tmp/prunin-ready.json").read_text())
assert r.get("status") == "ready", r
print("Container readiness:", r.get("model_version"), r.get("model_mode"))
PY
curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:${port}/api/genai-providers" > /tmp/prunin-genai-providers.json
python3 - <<'PY'
import json
from pathlib import Path
p = json.loads(Path("/tmp/prunin-genai-providers.json").read_text())
assert set(p) == {"ollama"}
assert p["ollama"]["provider"] == "ollama"
print("GenAI provider status endpoint: OK (Ollama only)")
PY
curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:${port}/metrics" | grep -q "prunin_"
echo "Container smoke: PASS (demo models only; no external LLM, no Kubernetes claim)"
