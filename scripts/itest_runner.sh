#!/usr/bin/env bash
set -euo pipefail

PYTEST_COMMON=(-c config/testing/pytest.ini -p no:xdist --timeout=300 -q -vv --log-cli-level=INFO --durations=20 --durations-min=0.1)

# Robust way to pass a -k expression without word-splitting issues
if [[ -n "${PYTEST_K:-}" ]]; then
  PYTEST_COMMON+=(-k "${PYTEST_K}")
fi

SKIP_STRESS="${ICE_SKIP_STRESS:-1}"
echo "[itest] ICE_SKIP_STRESS=${SKIP_STRESS}"

echo "[itest] Running ice_api suite..."
pytest "${PYTEST_COMMON[@]}" tests/integration/ice_api

echo "[itest] Running ice_core suite..."
pytest "${PYTEST_COMMON[@]}" tests/integration/ice_core

echo "[itest] Running root integration tests..."
pytest "${PYTEST_COMMON[@]}" tests/integration/test_working_schema_validation.py

echo "[itest] Running ice_orchestrator suite (per-file)..."
shopt -s nullglob
for f in tests/integration/ice_orchestrator/test_*.py; do
  # Respect infra-level stress skip to avoid OOM on constrained runners
  if [[ "${SKIP_STRESS}" == "1" && "$f" == *"test_resource_sandbox.py"* ]]; then
    echo "[itest] -> Skipping $f due to ICE_SKIP_STRESS=1"
    continue
  fi
  echo "[itest] -> $f"
  pytest "${PYTEST_COMMON[@]}" "$f"
done

echo "[itest] Running ice_client suite..."
pytest "${PYTEST_COMMON[@]}" tests/integration/ice_client

echo "[itest] All integration suites completed."
