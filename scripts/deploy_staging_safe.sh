#!/usr/bin/env bash
# Academic staging deployment: preflight candidate, promote, verify, rollback on failure.
# Dedicated Docker host only. Not zero-downtime, not production, not Kubernetes.
set -euo pipefail
cd "$(dirname "$0")/.."
image="${1:?Usage: bash scripts/deploy_staging_safe.sh image:tag}"
name="prunin-staging"
candidate="prunin-staging-candidate"
live_port="${PRUNIN_STAGING_PORT:-18767}"
test_port="${PRUNIN_STAGING_CANDIDATE_PORT:-18768}"
data_dir="${PRUNIN_STAGING_ARTIFACTS:-/opt/prunin-academic-artifacts/0.9.0-academic}"
envfile="${PRUNIN_STAGING_ENV:-/opt/prunin-staging/config.env}"

command -v docker >/dev/null
command -v curl >/dev/null
test -s "$envfile"
for file in health.joblib delay_days.joblib cost_overrun_ratio.joblib; do
  test -s "$data_dir/$file"
done
docker image inspect "$image" >/dev/null

run_container() {
  local container="$1" port="$2" image_ref="$3"
  docker run -d --name "$container" --restart unless-stopped \
    --publish "127.0.0.1:$port:8000" \
    --env-file "$envfile" \
    --mount "type=bind,source=$data_dir,target=/app/artifacts/0.9.0-academic,readonly" \
    --env PRUNIN_ARTIFACT_DIR=/app/artifacts/0.9.0-academic \
    "$image_ref" >/dev/null
}
check_ready() {
  local port="$1"
  for _ in $(seq 1 40); do
    if curl -fsS --max-time 3 "http://127.0.0.1:$port/api/ready" | python3 -c \
      'import json,sys; x=json.load(sys.stdin); assert x.get("status")=="ready" and x.get("model_version")=="0.9.0-academic"' \
      >/dev/null 2>&1; then return 0; fi
    sleep 2
  done
  return 1
}
old_image=""
if docker container inspect "$name" >/dev/null 2>&1; then
  old_image="$(docker inspect -f '{{.Config.Image}}' "$name")"
fi

# Validate the replacement image while the existing staging service is running.
docker rm -f "$candidate" >/dev/null 2>&1 || true
run_container "$candidate" "$test_port" "$image"
if ! check_ready "$test_port"; then
  docker logs "$candidate" --tail 70 || true
  docker rm -f "$candidate" >/dev/null 2>&1 || true
  echo "FAIL: candidate unhealthy; existing staging left untouched" >&2
  exit 1
fi
docker rm -f "$candidate" >/dev/null 2>&1 || true

# The local host swaps ports; this has a brief availability gap. Roll back
# to the previous immutable image if the promoted container is not ready.
docker rm -f "$name" >/dev/null 2>&1 || true
if run_container "$name" "$live_port" "$image" && check_ready "$live_port"; then
  echo "STAGING DEPLOYMENT PASS: $image (academic model ready)"
  exit 0
fi
docker logs "$name" --tail 70 || true
docker rm -f "$name" >/dev/null 2>&1 || true
if [[ -n "$old_image" ]]; then
  echo "New staging deployment failed; attempting rollback to $old_image" >&2
  if run_container "$name" "$live_port" "$old_image" && check_ready "$live_port"; then
    echo "ROLLBACK PASS: previous staging image restored" >&2
  else
    echo "ROLLBACK FAILURE: manual recovery required" >&2
  fi
else
  echo "No previously deployed image exists for rollback" >&2
fi
exit 1
