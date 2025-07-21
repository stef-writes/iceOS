"""Validate JSON/YAML syntax across the repository.

Run via::

    python -m scripts.cli.check_json_yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # Will skip YAML files if PyYAML missing.

# NEW: Try importing commentjson for JSONC support.
try:  # – nested try for optional import
    import commentjson  # type: ignore
except ImportError:  # pragma: no cover – optional dependency
    commentjson = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # ../../

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def iter_files(patterns: List[str]):
    for pattern in patterns:
        yield from REPO_ROOT.rglob(pattern)


def check_json(path: Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except Exception as exc:
        print(f"JSON syntax error in {path}: {exc}")
        return False


def check_yaml(path: Path) -> bool:
    if yaml is None:
        return True
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
        return True
    except Exception as exc:
        print(f"YAML syntax error in {path}: {exc}")
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Syntax check for JSON/YAML files.")
    parser.add_argument(
        "--patterns",
        nargs="*",
        default=["*.json", "*.jsonc", "*.yaml", "*.yml"],
        help="Glob patterns to include in the scan (default: *.json *.jsonc *.yaml *.yml).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    ok = True
    for file in iter_files(args.patterns):
        if file.suffix == ".json":
            ok &= check_json(file)
        elif file.suffix == ".jsonc":
            if commentjson is None:
                # Skip gracefully if commentjson not installed
                continue
            try:
                commentjson.loads(file.read_text(encoding="utf-8"))
            except Exception as exc:
                print(f"JSONC syntax error in {file}: {exc}")
                ok = False
        else:
            ok &= check_yaml(file)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
