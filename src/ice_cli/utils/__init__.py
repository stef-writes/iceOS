from __future__ import annotations

"""Shared helper utilities for the *ice_cli* package.

This module centralises small, broadly useful helpers so they are implemented
exactly once and can be imported by multiple sub-modules.  Keeping them here
avoids copy-pasted implementations sprinkled across *commands/* and *cli.py*.
"""

import re
from pathlib import Path

__all__ = ["snake_case", "pretty_path"]


def snake_case(name: str) -> str:  # noqa: D401 – simple helper
    """Convert *PascalCase* or *camelCase* names to ``snake_case``.

    This helper is intentionally *very* close to GitHub's own implementation
    (see `linguist`), so it works well for common patterns like `HTTPRequest` →
    ``http_request`` and `MyCoolTool` → ``my_cool_tool``.
    """

    # Split on boundary between "ABC" and "Xy"   → "ABC_ Xy"
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    # Split on boundary between "a" and "B"       → "a_ B"
    name = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)

    return name.replace("-", "_").lower()


def pretty_path(path: Path) -> str:  # noqa: D401 – helper
    """Return *path* relative to CWD if possible for nicer console output."""

    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _print_mermaid_graph(chain):  # noqa: D401 – helper
    """Print a Mermaid graph for the given chain."""
    # ... existing code for printing the graph ...
