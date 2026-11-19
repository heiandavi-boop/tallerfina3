#!/usr/bin/env bash
# Docker-only integration: two identical demo API replicas behind nginx.
# Explicitly tests routing and failover; does NOT claim Kubernetes HA or autoscaling.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null
command -v curl >/dev/null
image="${PRUNIN_SMOKE_IMAGE:-prunin-ai-core:rubric-smoke}"
port="${PRUNIN_HA_PORT:-18766}"
suffix="${GITHUB_RUN_ID:-$$}-$$"
network="prunin-ha-${suffix}"
first="prunin-ha-a-${suffix}"
second="prunin-ha-b-${suffix}"
proxy="prunin-ha-proxy-${suffix}"
tmpdir="$(mktemp -d)"
cleanup() {
  docker rm -f "$proxy" "$first" "$second" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
  rm -rf "$tmpdir"
}
trap cleanup EXIT

docker image inspect "$image" >/dev/null
docker network create "$network" >/dev/null
docker run -d --name "$first" --network "$network" --network-alias backend-a \
  -e PRUNIN_ARTIFACT_DIR=artifacts/demo-0.1.0 "$image" >/dev/null
docker run -d --name "$second" --network "$network" --network-alias backend-b \
  -e PRUNIN_ARTIFACT_DIR=artifacts/demo-0.1.0 "$image" >/dev/null
cat > "$tmpdir/nginx.conf" <<'CONF'
events {}
http {
    upstream prunin {
        server backend-a:8000 max_fails=1 fail_timeout=5s;
        server backend-b:8000 max_fails=1 fail_timeout=5s;
    }
    server {
        listen 8080;
        location / {
            proxy_pass http://prunin;
            proxy_connect_timeout 2s;
            proxy_read_timeout 10s;
            proxy_next_upstream error timeout http_502 http_503 http_504;
            proxy_next_upstream_tries 2;
        }
    }
}
CONF
docker run -d --name "$proxy" --network "$network" -p "127.0.0.1:${port}:8080" \
  -v "$tmpdir/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:1.27-alpine >/dev/null

url="http://127.0.0.1:${port}"
ready=0
for _ in $(seq 1 60); do
  if curl -fsS --max-time 2 "$url/api/ready" > "$tmpdir/ready.json" 2>/dev/null; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" != 1 ]]; then
  echo "Two-replica proxy never reached readiness"
  docker logs "$first" --tail 40 || true
  docker logs "$second" --tail 40 || true
  docker logs "$proxy" --tail 40 || true
  exit 1
fi
python3 - "$tmpdir/ready.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    assert json.load(stream)["status"] == "ready"
PY

# 40 independent client connections should reach both upstream containers.
for _ in $(seq 1 40); do
  curl -fsS --max-time 10 "$url/api/health" >/dev/null
done
served_first="$(docker logs "$first" 2>&1 | grep -c 'GET /api/health' || true)"
served_second="$(docker logs "$second" 2>&1 | grep -c 'GET /api/health' || true)"
if [[ "$served_first" -lt 1 || "$served_second" -lt 1 ]]; then
  echo "Both backends must serve requests: A=$served_first B=$served_second"
  exit 1
fi
echo "Load distribution: A=$served_first B=$served_second"

# Stop only A. Nginx should keep answering by routing to B.
docker stop "$first" >/dev/null
for _ in $(seq 1 20); do
  curl -fsS --retry 2 --retry-delay 1 --max-time 10 "$url/api/ready" >/dev/null
done
echo "Single-instance stop: proxy remained available"

# Manually restore the stopped instance; no auto-restart claim.
docker start "$first" >/dev/null
for _ in $(seq 1 40); do
  if docker exec "$first" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/ready', timeout=2)" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker exec "$first" python -c "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8000/api/ready', timeout=3).status == 200"
# Recover from an *unexpected process crash* using Docker's restart policy.
# This is distinct from an operator-initiated docker stop, which does not auto-restart.
docker update --restart unless-stopped "$first" >/dev/null
before="$(docker inspect -f '{{.RestartCount}}' "$first")"
# Docker restart manager requires the container to have run long enough
# to avoid a restart loop; the earlier readiness/load checks provide this.
docker kill --signal=SIGKILL "$first" >/dev/null
recovered=0
for _ in $(seq 1 45); do
  after="$(docker inspect -f '{{.RestartCount}}' "$first" 2>/dev/null || echo 0)"
  if [[ "$after" -gt "$before" ]] && docker exec "$first" python -c "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8000/api/ready',timeout=2).status == 200" >/dev/null 2>&1; then
    recovered=1
    break
  fi
  sleep 2
done
if [[ "$recovered" != 1 ]]; then
  echo "Docker policy did not recover crashed replica; FAIL"
  docker logs "$first" --tail 50 || true
  exit 1
fi
for _ in $(seq 1 20); do
  curl -fsS --retry 2 --retry-delay 1 --max-time 10 "$url/api/ready" >/dev/null
done
echo "Two-replica Docker failover AND crash auto-restart smoke: PASS (Docker only, not Kubernetes)"
