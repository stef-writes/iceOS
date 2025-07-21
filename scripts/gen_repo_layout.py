#!/usr/bin/env python3
"""Generate an up-to-date Repository Layout Markdown file.

This script traverses a small, curated set of top-level folders and emits
`docs/architecture/repo_layout.md` so that the architecture docs stay in sync
with the real file-tree.

Example
-------
$ poetry run python scripts/gen_repo_layout.py

It is designed to be called by *make refresh-docs* and CI hooks – **do not edit
`docs/architecture/repo_layout.md` by hand**.
"""
from __future__ import annotations

from pathlib import Path
from typing import Final, Iterable, List

# ---------------------------------------------------------------------------
# Configuration -------------------------------------------------------------
# ---------------------------------------------------------------------------
_OUTPUT_PATH: Final[Path] = Path("docs/architecture/repo_layout.md")
# Only include the folders that are relevant for readers – skip virtualenvs,
# caches and `.github`-style meta folders.
_ROOTS: Final[tuple[str, ...]] = (
    "src",
    "scripts",
    "tests",
    "docs",
    "data",
)
_EXCLUDE_DIRS: Final[frozenset[str]] = frozenset(
    {
        "__pycache__",
        ".venv",
        ".git",
        ".ruff_cache",
        ".mypy_cache",
        ".pytest_cache",
    }
)

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _iter_subdirs(path: Path) -> Iterable[Path]:
    """Yield *sorted* direct children that are not excluded."""
    return (
        child
        for child in sorted(path.iterdir(), key=lambda p: p.name)
        if child.name not in _EXCLUDE_DIRS
    )


def _build_tree(root: Path, prefix: str = "") -> List[str]:
    """Recursively build a `tree`-like representation starting at *root*."""
    lines: List[str] = []
    children = list(_iter_subdirs(root))
    for idx, child in enumerate(children):
        connector = "└── " if idx == len(children) - 1 else "├── "
        line = (
            f"{prefix}{connector}{child.name}/"
            if child.is_dir()
            else f"{prefix}{connector}{child.name}"
        )
        lines.append(line)
        if child.is_dir():
            extension = "    " if idx == len(children) - 1 else "│   "
            lines.extend(_build_tree(child, prefix + extension))
    return lines


# ---------------------------------------------------------------------------
# Main ----------------------------------------------------------------------
# ---------------------------------------------------------------------------


def main() -> None:  # – CLI entry-point
    """Write the *repo_layout.md* file under *docs/architecture*."""
    md_lines: List[str] = ["# Repository Layout (auto-generated)", "", "```text"]
    for root_name in _ROOTS:
        root_path = Path(root_name)
        if not root_path.exists():
            # Skip absent optional roots (e.g. data/ in fresh clone)
            continue
        md_lines.append(f"{root_name}/")
        md_lines.extend(_build_tree(root_path))
        md_lines.append("")  # blank line between root sections
    md_lines.append("```")

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT_PATH.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"[gen_repo_layout] wrote {_OUTPUT_PATH.relative_to(Path.cwd())}")


if __name__ == "__main__":  # pragma: no cover – script entry point only
    main()
