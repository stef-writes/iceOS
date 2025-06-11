from __future__ import annotations

"""Validate that all JSON and YAML files in the repo parse correctly."""

import json
import sys
from pathlib import Path
from typing import List

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # Will skip YAML files if PyYAML missing.

REPO_ROOT = Path(__file__).resolve().parent.parent


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
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    patterns = ["*.json", "*.yaml", "*.yml"]
    ok = True
    for file in iter_files(patterns):
        if file.name.endswith(".json"):
            ok &= check_json(file)
        else:
            ok &= check_yaml(file)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
