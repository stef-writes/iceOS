"""Generate CODEBASE_OVERVIEW.md with a simple package + class map.

This now writes to docs/codebase_overview.md to keep the project root tidy.

The script intentionally keeps output *brief* – one screen – so that Cursor
loads it entirely in context. For deeper docs use dedicated README files next
to the code.
"""
from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
from typing import List

from pydantic import BaseModel

OUTPUT_FILE = Path("docs") / "codebase_overview.md"
SRC_DIR = Path("src")
MAX_DEPTH = 2  # Only list packages up to this depth relative to src/


class PackageInfo(BaseModel):
    name: str  # dotted path, e.g. app.chains
    path: Path


# ---------------------------------------------------------------------------
# Introspection helpers
# ---------------------------------------------------------------------------


def gather_packages() -> List[PackageInfo]:
    """Return list of importable packages under SRC_DIR."""

    packages: list[PackageInfo] = []

    for path in SRC_DIR.rglob("__init__.py"):
        depth = len(path.relative_to(SRC_DIR).parents) - 1
        if depth > MAX_DEPTH:
            continue
        pkg_path = path.parent
        dotted = pkg_path.relative_to(SRC_DIR).as_posix().replace("/", ".")
        packages.append(PackageInfo(name=dotted, path=pkg_path))

    packages.sort(key=lambda p: p.name)
    return packages


def first_docstring_line(py_file: Path) -> str | None:
    """Return first non-empty line of module-level docstring if present."""

    try:
        module = ast.parse(py_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    if doc := ast.get_docstring(module):
        for line in doc.splitlines():
            cleaned = line.strip()
            if cleaned:
                return cleaned
    return None


def describe_package(pkg: PackageInfo) -> str:
    """Return one-line description for *pkg* based on its __init__.py docstring."""

    init_file = pkg.path / "__init__.py"
    line = first_docstring_line(init_file)
    return line or "(no description)"


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------


def build_markdown(pkgs: list[PackageInfo]) -> str:
    md_lines: list[str] = []
    md_lines.append("# Codebase Overview (auto-generated)")
    md_lines.append("")
    md_lines.append(
        f"> Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')} – run `make refresh-docs` to regenerate."
    )
    md_lines.append("")
    md_lines.append("## Packages")
    md_lines.append("")

    for pkg in pkgs:
        desc = describe_package(pkg)
        md_lines.append(f"- **`{pkg.name}`** – {desc}")

    md_lines.append("")
    md_lines.append(
        "(truncated at depth ≤ 2. For deeper docs see per-package README files.)"
    )
    md_lines.append("")
    md_lines.append(
        "See also `docs/capability_catalog.json` for a machine-readable registry."
    )

    return "\n".join(md_lines) + "\n"


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:  # noqa: D401 (imperative mood ok)
    pkgs = gather_packages()
    markdown = build_markdown(pkgs)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(markdown, encoding="utf-8")
    print(f"[gen_overview] Wrote {len(pkgs)} package entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
