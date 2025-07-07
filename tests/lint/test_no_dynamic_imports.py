from __future__ import annotations

import ast
import pathlib
from typing import List

# ---------------------------------------------------------------------------
# Configuration --------------------------------------------------------------
# ---------------------------------------------------------------------------

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"

# Whitelisted paths (relative to project root) that are allowed to use
# `importlib.import_module`.  Currently *only* the dedicated plugin discovery
# helper is exempt from the rule.
ALLOWED: set[str] = {
    "src/ice_sdk/plugin_discovery.py",
}


# ---------------------------------------------------------------------------
# Helpers --------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _uses_import_module(path: pathlib.Path) -> bool:  # noqa: D401 – small helper
    """Return *True* when *path* contains a call to `importlib.import_module`."""
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        # Skip files that fail to parse for any reason (unlikely in CI)
        return False

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# Test -----------------------------------------------------------------------
# ---------------------------------------------------------------------------


def test_no_importlib_import_module_usage_outside_allowed():
    """Fail when `importlib.import_module` is used in disallowed modules."""
    violations: List[str] = []

    for py in SRC_DIR.rglob("*.py"):
        rel = py.relative_to(ROOT).as_posix()
        if rel in ALLOWED:
            # Skip the explicitly allowed file
            continue

        if _uses_import_module(py):
            violations.append(rel)

    if violations:
        joined = "\n  - ".join(["", *violations])
        raise AssertionError(
            "`importlib.import_module` found in disallowed modules:" + joined
        )
