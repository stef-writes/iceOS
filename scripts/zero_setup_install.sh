#!/usr/bin/env bash
set -euo pipefail

echo "[iceOS] Zero-setup installer starting..."

# Check docker
if ! command -v docker >/dev/null 2>&1; then
  echo "[iceOS] Docker is required. Please install Docker Desktop first." >&2
  exit 1
fi

# Check docker compose
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  echo "[iceOS] docker compose is required (v2 recommended)." >&2
  exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$PROJECT_ROOT"

# Ensure Docker daemon is running
if ! docker info >/dev/null 2>&1; then
  echo "[iceOS] Docker daemon not running. Please start Docker Desktop and re-run." >&2
  exit 1
fi

# Create .env if missing and inject defaults
if [ ! -f .env ]; then
  echo "[iceOS] Creating .env with defaults"
  TOKEN=$(python - <<'PY'
import secrets, string
alphabet = string.ascii_letters + string.digits
print('tok_' + ''.join(secrets.choice(alphabet) for _ in range(24)))
PY
)
  {
    echo "ICE_API_TOKEN=${TOKEN}"
    echo "ORG_BUDGET_USD=5.00"
    echo "# OPENAI_API_KEY=sk-...  # optional for live LLM"
  } > .env
fi

echo "[iceOS] Using environment from .env:"
MASKED_TOKEN=$(grep '^ICE_API_TOKEN=' .env | cut -d= -f2- | sed -E 's/(.{0,2}).*(.{4})/\1****\2/') || true
[ -n "$MASKED_TOKEN" ] && echo "  ICE_API_TOKEN=${MASKED_TOKEN}" || true
echo "  ORG_BUDGET_USD=$(grep '^ORG_BUDGET_USD=' .env | cut -d= -f2- | tr -d '\n')"
if grep -q '^OPENAI_API_KEY=' .env 2>/dev/null; then
  if [ -n "$(grep '^OPENAI_API_KEY=' .env | cut -d= -f2-)" ]; then
    echo "  OPENAI_API_KEY=set"
  else
    echo "  OPENAI_API_KEY=unset"
  fi
fi

echo "[iceOS] Starting stack with ${COMPOSE}"
${COMPOSE} up -d --build

# Wait for readiness
API_URL="http://localhost:8000"
echo "[iceOS] Waiting for API readiness at ${API_URL}/readyz ..."
ATTEMPTS=60
until curl -fsS "${API_URL}/readyz" >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS-1))
  [ $ATTEMPTS -le 0 ] && { echo "[iceOS] API did not become ready in time" >&2; exit 1; }
  sleep 1
done

echo "[iceOS] API ready at ${API_URL}"

# Open browser if available (macOS / Linux)
if command -v open >/dev/null 2>&1; then
  open "${API_URL}/docs" || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "${API_URL}/docs" || true
fi

echo ""
echo "[iceOS] Done. Quickstart:"
RAW_TOKEN=$(grep '^ICE_API_TOKEN=' .env | cut -d= -f2-)
SHOW_TOKEN=$(echo "$RAW_TOKEN" | sed -E 's/(.{0,2}).*(.{4})/\1****\2/')
echo "  Token  : ${SHOW_TOKEN}  (full value in .env)"
echo "  API    : ${API_URL}"
echo "  Docs   : ${API_URL}/docs"
echo "  SSE    : MCP runs at /api/v1/mcp/runs + /runs/{id}/events"
echo ""
echo "Examples:"
echo "  curl -s -H 'Authorization: Bearer $(grep '^ICE_API_TOKEN=' .env | cut -d= -f2)' ${API_URL}/api/v1/meta/registry/health"
echo ""
