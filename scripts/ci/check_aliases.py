#!/usr/bin/env python
"""CI helper – fail if legacy node type aliases appear in source tree.

Usage: ``python scripts/ci/check_aliases.py``

The script scans all ``.json``, ``.jsonc``, ``.yaml``, ``.yml``, and ``.md`` files
plus Python source for patterns where node discriminators are specified and
asserts none of the **forbidden aliases** (`ai`, `prebuilt`, `subdag`) occur.

• Exits with status **1** on violation; prints offending file/line numbers.
• Intended to be run by Makefile/CI job prior to tests.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Configuration --------------------------------------------------------------
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]  # repo root
PATTERNS: List[str] = [
    r"\"type\"\s*:\s*\"ai\"",
    r"\"type\"\s*:\s*\"prebuilt\"",
    r"\"type\"\s*:\s*\"subdag\"",
    r"\"type\"\s*:\s*\"skill\"",
]
FILE_GLOBS = ["**/*.json", "**/*.jsonc", "**/*.yml", "**/*.yaml", "**/*.md", "**/*.py"]


def scan_file(path: Path) -> List[str]:
    """Return list of violation strings for *path*."""

    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []  # ignore binary or unreadable

    violations = []
    for pattern in PATTERNS:
        for m in re.finditer(pattern, text):
            line_no = text.count("\n", 0, m.start()) + 1
            alias = m.group(0)
            violations.append(f"{path}:{line_no}: {alias}")
    return violations


def main() -> None:  # noqa: D401 – entrypoint
    all_violations: List[str] = []

    for glob in FILE_GLOBS:
        for fp in ROOT.glob(glob):
            all_violations.extend(scan_file(fp))

    if all_violations:
        print("Legacy node type aliases detected:\n" + "\n".join(all_violations), file=sys.stderr)
        sys.exit(1)

    print("Alias check passed – no legacy node type aliases found.")


if __name__ == "__main__":
    main() 