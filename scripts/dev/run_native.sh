#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

export NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:8000}
export NEXT_PUBLIC_API_TOKEN=${NEXT_PUBLIC_API_TOKEN:-dev-token}
export ICE_ALLOW_DEV_TOKEN=${ICE_ALLOW_DEV_TOKEN:-1}

API_LOG="$ROOT_DIR/.logs/api-dev.log"
WEB_LOG="$ROOT_DIR/.logs/web-dev.log"
mkdir -p "$ROOT_DIR/.logs"

echo "[native] Starting API (uvicorn) ..."
(
  USE_FAKE_REDIS=1 PYTHONPATH=src:. uvicorn ice_api.main:app \
    --host 0.0.0.0 --port 8000 --reload \
    >"$API_LOG" 2>&1
) & API_PID=$!

trap 'echo "[native] Stopping..."; kill -9 $API_PID >/dev/null 2>&1 || true; kill -9 $WEB_PID >/dev/null 2>&1 || true' EXIT

echo "[native] Waiting for API readiness at $NEXT_PUBLIC_API_URL/readyz ..."
for i in $(seq 1 90); do
  if curl -fsS "$NEXT_PUBLIC_API_URL/readyz" >/dev/null 2>&1; then
    echo "[native] API ready"
    break
  fi
  sleep 1
  if [ "$i" -eq 90 ]; then
    echo "[native] API did not become ready in time. See $API_LOG" >&2
    exit 1
  fi
done

echo "[native] Starting frontend (next dev) ..."
(
  cd frontend/apps/web && \
  npm run dev \
    >"$WEB_LOG" 2>&1
) & WEB_PID=$!

echo "[native] Running. Web → http://localhost:3000  |  API → $NEXT_PUBLIC_API_URL"
wait $WEB_PID
