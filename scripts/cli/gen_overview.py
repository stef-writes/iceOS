from __future__ import annotations

"""CLI entrypoint for codebase overview generation.

Delegates to the legacy :pyfile:`scripts/gen_overview.py` implementation.
"""

from pathlib import Path
import runpy
import sys

LEGACY_PATH = Path(__file__).resolve().parent.parent / "gen_overview.py"

if not LEGACY_PATH.exists():
    sys.exit("Legacy gen_overview.py not found. Please update your installation.")


if __name__ == "__main__":
    runpy.run_path(str(LEGACY_PATH), run_name="__main__") 