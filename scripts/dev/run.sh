#!/usr/bin/env bash
set -euo pipefail

echo "[run] Preflight: checking Docker daemon..."
docker version >/dev/null 2>&1 || {
  echo "[run] Docker not ready. Attempting to start Docker Desktop..." >&2
  if command -v open >/dev/null 2>&1; then
    open -a Docker || true
  fi
  for i in $(seq 1 120); do
    if docker version >/dev/null 2>&1; then
      echo "[run] Docker is ready"
      break
    fi
    sleep 2
    if [ "$i" -eq 120 ]; then
      echo "[run] Docker did not become ready within timeout. Please start Docker Desktop and retry: make run" >&2
      exit 1
    fi
  done
}

export NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost}
export NEXT_PUBLIC_API_TOKEN=${NEXT_PUBLIC_API_TOKEN:-dev-token}

# Secret sourcing (non-interactive): ~/.config/iceos/keys.env → macOS Keychain → env
echo "[run] Loading provider keys (non-interactive) ..."
CONFIG_DIR="$HOME/.config/iceos"
KEYS_ENV="$CONFIG_DIR/keys.env"
if [ -f "$KEYS_ENV" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$KEYS_ENV"
  set +a
  echo "[run] Loaded keys from $KEYS_ENV"
fi

# macOS Keychain fallback (do not fail if not present)
if command -v security >/dev/null 2>&1; then
  if [ -z "${OPENAI_API_KEY:-}" ]; then OPENAI_API_KEY=$(security find-generic-password -s iceos-openai -w 2>/dev/null || true); export OPENAI_API_KEY; fi
  if [ -z "${ANTHROPIC_API_KEY:-}" ]; then ANTHROPIC_API_KEY=$(security find-generic-password -s iceos-anthropic -w 2>/dev/null || true); export ANTHROPIC_API_KEY; fi
  if [ -z "${GOOGLE_API_KEY:-}" ]; then GOOGLE_API_KEY=$(security find-generic-password -s iceos-google -w 2>/dev/null || true); export GOOGLE_API_KEY; fi
  if [ -z "${DEEPSEEK_API_KEY:-}" ]; then DEEPSEEK_API_KEY=$(security find-generic-password -s iceos-deepseek -w 2>/dev/null || true); export DEEPSEEK_API_KEY; fi
fi

echo "[run] Providers active: \c"
ACTIVE=()
[ -n "${OPENAI_API_KEY:-}" ] && ACTIVE+=("openai")
[ -n "${ANTHROPIC_API_KEY:-}" ] && ACTIVE+=("anthropic")
[ -n "${GOOGLE_API_KEY:-}" ] && ACTIVE+=("google")
[ -n "${DEEPSEEK_API_KEY:-}" ] && ACTIVE+=("deepseek")
echo "${ACTIVE[*]:-none}" | sed 's/ /,/g'

echo "[run] Bringing up databases and cache..."
docker compose up -d --build --remove-orphans postgres redis

echo "[run] Running migrations..."
docker compose run --rm migrate

echo "[run] Starting API and Frontend..."
docker compose up -d --build --remove-orphans api web

echo "[run] Waiting for API readiness at $NEXT_PUBLIC_API_URL/readyz ..."
for i in $(seq 1 120); do
  if curl -fsS "$NEXT_PUBLIC_API_URL/readyz" >/dev/null 2>&1; then
    echo "[run] API ready"
    break
  fi
  sleep 1
  if [ "$i" -eq 120 ]; then
    echo "[run] API did not become ready in time" >&2
    exit 1
  fi
done

echo "[run] Services running:"
docker compose ps
echo "[run] Web -> http://localhost:3000"
echo "[run] API -> $NEXT_PUBLIC_API_URL"
