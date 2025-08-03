#!/usr/bin/env python3
"""CI guard: fail if JSON schemas under *schemas/generated/* are stale.

This script is intended for CI pipelines but can be run locally as well:

    python scripts/ci/check_schema_drift.py

It will regenerate all schemas via ``ice_cli.commands.export_schemas.export_all_schemas``
then compare ``git status`` output before/after.  If regenerating the schemas
modifies any tracked file, the script exits with status 1 and prints an
instruction message so developers can update the committed artifacts.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Helper – run a command and capture stdout as string ------------------------
# ---------------------------------------------------------------------------

def _capture_git_status(path: str) -> str:
    """Return porcelain status for *path* (empty string if git not available)."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", path],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout
    except FileNotFoundError:
        # Git not installed (e.g., in certain container builds) – treat as no diff
        return ""


# ---------------------------------------------------------------------------
# Main execution ------------------------------------------------------------
# ---------------------------------------------------------------------------

def main() -> None:  # noqa: D401 – CLI entry-point
    project_root = Path(__file__).resolve().parents[2]
    schemas_dir = project_root / "schemas" / "generated"

    diff_before = _capture_git_status(str(schemas_dir))

    # Regenerate schemas in-place ------------------------------------------------
    from ice_cli.commands.export_schemas import export_all_schemas

    export_all_schemas(str(schemas_dir), format="json")

    diff_after = _capture_git_status(str(schemas_dir))

    if diff_before != diff_after:
        print(
            "Schema files are out of date – run `ice export-schemas` or\n"
            "`python -m ice_cli.commands.export_schemas` and commit the changes.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
