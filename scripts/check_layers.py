"""Simple guard preventing cross-layer imports.

This is **not** a full-blown import-linter replacement – it is fast enough to
run in pre-commit and CI.  When it detects a violation, it prints a readable
error and exits with status 1.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Allowed cross-service dependencies (single source of truth) ----------------
# ---------------------------------------------------------------------------
# Key   = service owning the *calling* file  (src/<service>/...)
# Value = list of other top-level services it may import from.
# If a service is *absent* from the map we assume **no** external imports.
# ---------------------------------------------------------------------------

ALLOWED_DEPENDENCIES: dict[str, list[str]] = {
    "ice_cli": ["ice_core", "ice_client", "ice_orchestrator"],  # CLI needs client for remote, orchestrator for local
    "ice_api": ["ice_core", "ice_orchestrator"],  # API delegates to orchestrator
    "ice_client": ["ice_core"],  # Client only needs core models
    "ice_builder": ["ice_core"],  # Builder creates structures using core models
    "ice_orchestrator": ["ice_core", "ice_tools"],  # Runtime depends on core and built-in tools
    "ice_tools": ["ice_core"],  # Built-in tools depend only on core
    "frosty": ["ice_core", "ice_builder"],  # CLI only
    "frosty.core": ["ice_core", "ice_builder"],
    "frosty.codegen": ["ice_core", "ice_builder"],
    "ice_core": [],  # Foundation layer - no external dependencies
}


# ---------------------------------------------------------------------------
# Core validator ------------------------------------------------------------
# ---------------------------------------------------------------------------


def validate_imports() -> int:
    """Return number of layer violations found across *src/*.py* files."""

    errors = 0
    src_root = Path(__file__).resolve().parent.parent / "src"

    for py_file in src_root.rglob("*.py"):
        # Determine the *declaring* service (e.g. src/ice_sdk/… -> ice_sdk)
        try:
            current_service = py_file.relative_to(src_root).parts[0]
        except ValueError:
            # Should not happen – defensive guard
            continue

        allowed = ALLOWED_DEPENDENCIES.get(current_service, [])

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            print(f"Syntax error while parsing {py_file}: {exc}")
            errors += 1
            continue

        for node in ast.walk(tree):
            imported_root: str | None = None

            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_root = alias.name.split(".")[0]
                    if _is_forbidden(imported_root, current_service, allowed):
                        _report(py_file, imported_root, allowed)
                        errors += 1

            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                imported_root = node.module.split(".")[0]
                if _is_forbidden(imported_root, current_service, allowed):
                    _report(py_file, imported_root, allowed)
                    errors += 1

    return errors


def _is_forbidden(imported_root: str, current_service: str, allowed: list[str]) -> bool:
    """Return True if *imported_root* is a *service* outside the allowed list."""

    if not imported_root.startswith("ice_"):
        return False  # We only care about cross-service imports
    if imported_root == current_service:
        return False  # Self-import – always OK
    return imported_root not in allowed


def _report(py_file: Path, imported: str, allowed: list[str]) -> None:
    print(f"VIOLATION: {py_file} imports {imported} (allowed: {allowed or 'none'})")


# ---------------------------------------------------------------------------
# CLI entry-point -----------------------------------------------------------
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry-point so the script can be run via *python scripts/check_layers.py*."""

    parser = argparse.ArgumentParser(description="Validate cross-layer imports")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error on *any* violation (default).",
    )

    _ = parser.parse_args()  # Currently unused – placeholder for future options

    violations = validate_imports()
    if violations:
        print(f"Layer guard: {violations} violation(s) detected.")
        sys.exit(1)

    print("Layer guard: all good.")


if __name__ == "__main__":  # pragma: no cover
    main()
