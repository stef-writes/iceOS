"""Ensure core packages never import from the *samples* namespace.

The rule prevents accidental coupling between production code and examples.
The test parses each ``.py`` file under *src/* and fails if it finds any
``import samples`` or ``from samples.`` statement.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import List, Set

SRC_ROOT = Path(__file__).resolve().parents[3] / "src"


def _find_offending_imports(file_path: Path) -> Set[str]:
    """Return offending import strings in *file_path* (if any)."""
    offenders: set[str] = set()
    try:
        tree = ast.parse(file_path.read_text())
    except (SyntaxError, UnicodeDecodeError):  # pragma: no cover – legacy/unparseable
        return offenders

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("samples"):
                    offenders.add(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("samples"):
                offenders.add(f"from {node.module} import …")

    return offenders


def test_no_samples_import_in_src() -> None:  # noqa: D401
    """Fail if any production module imports from *samples*.*."""

    offenders: List[str] = []
    for root, _dirs, files in os.walk(SRC_ROOT):
        for filename in files:
            if not filename.endswith(".py"):
                continue
            fp = Path(root) / filename
            bad = _find_offending_imports(fp)
            offenders.extend(f"{fp}: {imp}" for imp in bad)

    assert not offenders, (
        "Production code must not import from samples.* (example namespace).\n"
        + "\n".join(offenders)
    )
