#!/usr/bin/env bash

# ---------------------------------------------------------------------------
# Development helper to run the FastAPI server in *reload* mode.
#
# Usage:
#   1. python -m venv .venv && source .venv/bin/activate
#   2. pip install -r requirements.txt
#   3. ./start_server.sh
#
# The script looks for *uvicorn* in the active virtual-environment first; if not
# activated it falls back to ``.venv/bin/uvicorn`` when that path exists.
# ---------------------------------------------------------------------------

set -euo pipefail

# Resolve uvicorn binary ------------------------------------------------------
if command -v uvicorn >/dev/null 2>&1; then
  UVICORN_BIN="$(command -v uvicorn)"
elif [ -x ".venv/bin/uvicorn" ]; then
  UVICORN_BIN=".venv/bin/uvicorn"
else
  echo "Error: uvicorn not found. Activate your virtualenv or install requirements." >&2
  exit 1
fi

# Ensure application sources are on PYTHONPATH
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"

# Launch the FastAPI app with auto-reload enabled --------------------------------
exec "${UVICORN_BIN}" app.main:app --reload 