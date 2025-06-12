"""Ensure every Python source file contains the required license header.

By default the script looks for the string "MIT License" within the first
10 lines of each ``*.py`` file.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # ../../
LICENSE_STRING_DEFAULT = "MIT License"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def file_has_header(path: Path, needle: str, max_lines: int) -> bool:
    try:
        with path.open("r", encoding="utf-8") as f:
            for _ in range(max_lines):
                line = f.readline()
                if not line:
                    break
                if needle in line:
                    return True
    except Exception as exc:
        print(f"Failed to read {path}: {exc}")
    return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:  # noqa: D401
    parser = argparse.ArgumentParser(description="License header checker")
    parser.add_argument(
        "--license-string",
        default=LICENSE_STRING_DEFAULT,
        help='String to search for in header (default: "MIT License")',
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=10,
        help="Number of top-of-file lines to scan (default: 10)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    missing: list[Path] = []
    for py_file in REPO_ROOT.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        if not file_has_header(py_file, args.license_string, args.max_lines):
            missing.append(py_file)

    if missing:
        print("Files missing license header:")
        for path in missing:
            print(f" - {path.relative_to(REPO_ROOT)}")
        sys.exit(1)
    else:
        print("All files contain license header ✔️")
        sys.exit(0)


if __name__ == "__main__":
    main() 