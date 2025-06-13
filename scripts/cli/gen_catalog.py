"""CLI entrypoint for capability catalog generation.

This is a thin wrapper around :pyfile:`scripts/gen_catalog.py` so that
external callers can use the consistent ``scripts.cli`` namespace without
breaking existing imports.

In a follow-up release the legacy module will be removed.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

# Make sure we execute the *source* file so that relative imports & paths
# inside it continue to resolve correctly.
LEGACY_PATH = Path(__file__).resolve().parent.parent / "gen_catalog.py"

if not LEGACY_PATH.exists():
    sys.exit("Legacy gen_catalog.py not found. Please update your installation.")


if __name__ == "__main__":
    runpy.run_path(str(LEGACY_PATH), run_name="__main__") 