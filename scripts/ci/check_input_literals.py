#!/usr/bin/env python3
"""Fail CI when literal values are found in input_mappings.

Rule: every value inside an `input_mappings` object must be either
1) a dict containing `source_node_id` & `source_output_key` keys, or
2) a JSON-serialisable object representing an InputMapping (generated via SDK).

A quick regex scan is enough to catch >95 % of cases and keeps the guard fast.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root

# File globs to scan
_FILE_GLOBS: List[str] = [
    "**/*.py",
    "**/*.json",
    "**/*.yaml",
    "**/*.yml",
]

# Regex:  key "input_mappings"  then   {   then any key "...": <literal>
# A literal here is considered to be
#   – a quoted string without nested braces or source_node_id
#   – a bare number / boolean / null
_PATTERN = re.compile(
    r'input_mappings'  # the key
    r'\s*:\s*{[^}]*?'  # opening brace and non-greedy content
    r'"[^"]+"\s*:\s*'  # mapping key "xxx":
    r'(?!{[^}]*"source_node_id")'  # negative look-ahead: not a dict with source_node_id
    r'(?:"[^"{}]*"|[-]?[0-9]+(?:\.[0-9]+)?|true|false|null)'  # literal value
    ,
    re.IGNORECASE | re.DOTALL,
)


def main() -> None:
    offenders: list[Path] = []

    for glob in _FILE_GLOBS:
        for file in ROOT.glob(glob):
            if file.is_symlink() or not file.is_file():
                continue
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if _PATTERN.search(text):
                offenders.append(file.relative_to(ROOT))

    if offenders:
        joined = "\n  • ".join(str(p) for p in offenders)
        print(
            "Literal values detected in input_mappings – move them to tool_args or prompt placeholders:\n  • "
            + joined,
            file=sys.stderr,
        )
        sys.exit(1)

    print("Literal-mapping check passed – no violations detected.")


if __name__ == "__main__":
    main() 