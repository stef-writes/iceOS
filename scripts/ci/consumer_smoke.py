"""Smoke-test that iceOS wheel installs cleanly and that a consumer-style
sample can import and run against the installed distribution.

This script is executed inside GitHub Actions by the *consumer-samples* job:
1. `poetry build -f wheel` creates a wheel in `dist/`.
2. That wheel is installed into an isolated virtualenv *consumer_env*.
3. This script removes the local *src/* path from *sys.path* to guarantee we
   import the installed wheel (not the live checkout), then runs a minimal
   sample.

It exits with non-zero status if anything fails, triggering a CI failure.
"""

from __future__ import annotations

import pathlib
import sys

# ---------------------------------------------------------------------------
# Ensure we import the *installed* wheel, not the live source checkout.
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC_PATH = REPO_ROOT / "src"

if str(SRC_PATH) in sys.path:
    sys.path.remove(str(SRC_PATH))

# At this point, importing `ice_sdk` should resolve to the wheel

# ---------------------------------------------------------------------------
# Run the marketing demo as a real consumer would
# ---------------------------------------------------------------------------

from samples.marketing_chain import create_marketing_chain  # – after sys.path fix

chain = create_marketing_chain()

# Simple assertion: chain compiles & carries the expected identifier
assert chain.id == "MarketingCopyDemo", "Unexpected chain ID from sample"

print("[consumer_smoke] Sample chain built successfully – wheel import verified.")
