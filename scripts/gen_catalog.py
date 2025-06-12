"""Generate CAPABILITY_CATALOG.json by statically analysing the codebase.

This script is intentionally *import-side-effect free*: it relies on the standard
library (ast / pathlib / json) so it can run in any environment without needing
third-party packages and without importing the application itself – thereby
avoiding execution of user code while we are merely inspecting it.

This now writes to docs/capability_catalog.json so that generated
artifacts live alongside other documentation instead of cluttering
the project root.
"""
from __future__ import annotations

import ast
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Literal, Optional

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: Paths (relative to repo root) that we want to scan for capabilities.
SEARCH_ROOTS: tuple[str, ...] = ("src",)

#: Class name suffix → capability kind mapping fallback
SUFFIX_KIND_MAP: dict[str, str] = {
    "Node": "node",
    "Tool": "tool",
    "Agent": "agent",
    "Chain": "chain",
}

#: Name of the output JSON file (relative to repo root)
OUTPUT_FILE = Path("docs") / "capability_catalog.json"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

KindLiteral = Literal["node", "tool", "agent", "chain"]


class Capability(BaseModel):
    """One entry in the catalog."""

    id: str  # Fully-qualified name, e.g. app.tools.sql_query_tool.SQLQueryTool
    kind: KindLiteral
    path: str  # File path relative to repo root


class Catalog(BaseModel):
    """Top-level catalog schema."""

    generated_at: datetime
    capabilities: List[Capability]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def discover_py_files() -> Iterable[Path]:
    """Yield all *.py files under SEARCH_ROOTS."""

    for root in SEARCH_ROOTS:
        for path in Path(root).rglob("*.py"):
            # Skip common virtual-env / cache folders.
            if any(part.startswith("__pycache__") for part in path.parts):
                continue
            yield path


def guess_kind(class_name: str) -> Optional[KindLiteral]:
    """Infer capability kind from class name suffix.

    Falls back to *None* if no mapping matches.
    """

    for suffix, kind in SUFFIX_KIND_MAP.items():
        if class_name.endswith(suffix):
            return kind  # type: ignore[return-value]
    return None


class ClassCollector(ast.NodeVisitor):
    """Collect top-level class definitions via AST parsing."""

    def __init__(self) -> None:
        self.definitions: list[str] = []

    def visit_ClassDef(
        self, node: ast.ClassDef
    ) -> None:  # noqa: N802 (ast uses camelCase)
        self.definitions.append(node.name)
        # We don't need to traverse deeper for this use-case


def analyse_file(path: Path, project_root: Path) -> list[Capability]:
    """Return Capability entries for given Python *path*."""

    rel_path = path.relative_to(project_root).as_posix()
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    collector = ClassCollector()
    collector.visit(tree)

    capabilities: list[Capability] = []
    module_qualname = rel_path[:-3].replace("/", ".")  # strip .py

    for class_name in collector.definitions:
        kind = guess_kind(class_name)
        if kind is None:
            continue
        cap_id = f"{module_qualname}.{class_name}"
        capabilities.append(Capability(id=cap_id, kind=kind, path=rel_path))

    return capabilities


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:  # noqa: D401 (imperative mood is fine)
    """Collect capabilities and write JSON catalog."""

    project_root = Path(__file__).resolve().parent.parent
    all_caps: list[Capability] = []

    for py_file in discover_py_files():
        all_caps.extend(analyse_file(py_file, project_root=project_root))

    # Sort for deterministic output.
    all_caps.sort(key=lambda c: c.id)

    catalog = Catalog(generated_at=datetime.utcnow(), capabilities=all_caps)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(catalog.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(
        f"[gen_catalog] Wrote {len(all_caps)} capabilities to {OUTPUT_FILE}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
