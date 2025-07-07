"""CI helper script to validate all FlowSpec JSON files under *examples/flows/*
against ``schemas/flow_spec_v0.1.json``.

Usage
-----
python -m scripts.check_flow_spec  # exits non-zero on first validation error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover
    print("jsonschema package not installed – skipping FlowSpec validation")
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "flow_spec_v0.1.json"
FLOW_DIR = ROOT / "examples" / "flows"


def load_schema() -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_file(filepath: Path, schema: dict) -> None:
    with filepath.open("r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        jsonschema.validate(instance=data, schema=schema)  # type: ignore[arg-type]
    except jsonschema.ValidationError as exc:  # type: ignore[attr-defined]
        raise ValueError(f"{filepath}: {exc.message}") from exc


def main() -> None:  # noqa: D401
    schema = load_schema()
    errors: list[str] = []

    for json_file in FLOW_DIR.rglob("*.json"):
        try:
            validate_file(json_file, schema)
        except ValueError as err:
            errors.append(str(err))

    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        sys.exit(1)

    print("All FlowSpec files valid (", len(list(FLOW_DIR.rglob("*.json"))), "files)")


if __name__ == "__main__":
    main()
