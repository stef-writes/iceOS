"""Fail CI when source files import legacy vocabulary names.

This guards against re-introducing *AiNodeConfig* or *ToolNodeConfig*
after the v2 naming migration (LLMOperatorConfig / SkillNodeConfig).

Only **production** sources are scanned (``src/``).  Test fixtures may still
reference legacy names until they are gradually migrated.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Config --------------------------------------------------------------------
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent  # repo root
SRC_DIR = ROOT_DIR / "src"

# Legacy symbols to forbid ---------------------------------------------------
PATTERNS = [
    re.compile(r"\bAiNodeConfig\b"),
    re.compile(r"\bToolNodeConfig\b"),
]

# Files that legitimately define alias classes remain allowed ----------------
ALLOWED_FILES = {
    SRC_DIR / "ice_sdk" / "models" / "node_models.py",  # defines aliases
}


def _iter_py_files(base: Path):  # noqa: D401 – helper
    """Yield all ``*.py`` files under *base* recursively."""

    for path in base.rglob("*.py"):
        if path.is_file():
            yield path


@pytest.mark.parametrize("file_path", list(_iter_py_files(SRC_DIR)))
def test_no_legacy_vocabulary(file_path: Path) -> None:  # noqa: D401 – lint guard
    """Fail when legacy vocabulary appears in *file_path*."""

    if file_path in ALLOWED_FILES:
        return  # skip allowed files

    text = file_path.read_text(encoding="utf-8")
    for rx in PATTERNS:
        match = rx.search(text)
        assert (
            match is None
        ), f"Legacy symbol '{match.group(0)}' found in {file_path.relative_to(ROOT_DIR)}" 