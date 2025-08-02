"""Run all doc generators.

Will exit with status 1 if running would modify any generated file (for CI).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# List of generator entry-points (module paths)
GENERATORS = [
    "scripts.gen_docs.generate_architecture",
    "scripts.gen_docs.generate_config",
    "scripts.gen_docs.generate_manifest",
    "scripts.gen_docs.generate_protocols",
]


def main() -> None:
    # Capture git before state
    diff_before = subprocess.run(["git", "status", "--porcelain", "docs/generated"], capture_output=True, text=True, check=False).stdout

    # Run generators
    for mod in GENERATORS:
        __import__(mod, fromlist=["build"]).build()

    diff_after = subprocess.run(["git", "status", "--porcelain", "docs/generated"], capture_output=True, text=True, check=False).stdout

    if diff_before != diff_after:
        print("Docs are out of date – run `python scripts/gen_docs/build_all.py` and commit the changes.")
        sys.exit(1)


if __name__ == "__main__":
    main()
