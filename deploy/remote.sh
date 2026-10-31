#!/usr/bin/env bash
# Existing Docker host only. No infrastructure creation. Run from repo root.
set -euo pipefail
image="${1:?Usage: deploy/remote.sh qminh19/voicescope@sha256:DIGEST}"
[[ "$image" =~ ^qminh19/voicescope@sha256:[a-f0-9]{64}$ ]] || { echo 'Require immutable approved image'; exit 2; }
state=.deploy-state
mkdir -p "$state"
previous=$(cat "$state/current" 2>/dev/null || true)
export VOICESCOPE_IMAGE="$image"
docker compose -f compose.production.yaml pull
if docker compose -f compose.production.yaml up -d --wait --wait-timeout 180 &&
   python3 tools/container_smoke.py --output artifacts/deploy-smoke.json; then
  printf '%s' "$previous" > "$state/previous"
  printf '%s' "$image" > "$state/current"
  echo "Deployed $image"
else
  if [[ -n "$previous" ]]; then
    export VOICESCOPE_IMAGE="$previous"
    docker compose -f compose.production.yaml up -d --wait --wait-timeout 180
    echo 'Restored previous image after failed health/inference check'
  fi
  exit 1
fi
