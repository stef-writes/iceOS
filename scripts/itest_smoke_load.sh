#!/usr/bin/env bash
set -euo pipefail

# Simple RPS smoke test against /api/v1/executions/health path equivalents
# Usage: scripts/itest_smoke_load.sh http://localhost 50

BASE_URL=${1:-http://localhost}
CONCURRENCY=${2:-50}

echo "[smoke] Hitting ${BASE_URL}/readyz with concurrency=${CONCURRENCY} for 5 seconds"
command -v hey >/dev/null 2>&1 || { echo "Please install 'hey' (https://github.com/rakyll/hey)" >&2; exit 1; }
hey -z 5s -c "${CONCURRENCY}" "${BASE_URL}/readyz"
