#!/usr/bin/env bash
set -euo pipefail

PYTEST_COMMON=(-c config/testing/pytest.ini -p no:xdist -q -vv --log-cli-level=INFO --durations=20 --durations-min=0.1)
# Always exclude legacy test path if present in image
PYTEST_COMMON+=(-k "not test_rag_agent_demo")

# Robust way to pass a -k expression without word-splitting issues
if [[ -n "${PYTEST_K:-}" ]]; then
  PYTEST_COMMON+=(-k "${PYTEST_K}")
fi

SKIP_STRESS="${ICE_SKIP_STRESS:-1}"
echo "[itest] ICE_SKIP_STRESS=${SKIP_STRESS}"

echo "[itest] Running all integration tests in a single invocation..."
pytest "${PYTEST_COMMON[@]}" tests/integration
echo "[itest] All integration suites completed."
