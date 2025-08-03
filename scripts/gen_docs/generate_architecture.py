"""Generate architecture overview markdown fragment.

This enhanced generator produces `docs/generated/architecture_auto.md` with a
comprehensive, always-up-to-date overview of the codebase architecture. In
addition to the previous high-level diagram, it now includes:

1. A layer responsibility table augmented with the **count of Python modules**
   contained in each layer – provides quick insight into package size.
2. A **node-type table** mapping every `NodeType` value to its concrete
   `*NodeConfig` implementation along with the first line of its docstring. This
   keeps design docs in sync whenever new node types are introduced.

The file intentionally avoids any heavy introspection or runtime imports beyond
lightweight `inspect` usage, so execution time remains negligible.
"""

from __future__ import annotations

import inspect
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple, cast

from ice_core.models.node_models import BaseNodeConfig

# ---------------------------------------------------------------------------
# Paths ----------------------------------------------------------------------
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]  # project root (…/iceOSv1(A))
SRC_DIR = ROOT / "src"
DOC_OUT_DIR = ROOT / "docs" / "generated"
DOC_OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Static layer metadata ------------------------------------------------------
# ---------------------------------------------------------------------------

LayerTuple = Tuple[str, str, str]  # (package, responsibilities, may-import-from)

LAYERS: List[LayerTuple] = [
    ("ice_api", "HTTP/WS gateway, validation, persistence", "orchestrator, core"),
    ("ice_orchestrator", "Runtime engine – executes workflows", "core"),
    ("ice_builder", "Author-time DSLs & toolkits", "core"),
    ("ice_core", "Pure models, protocols, registry", "—"),
]

# ---------------------------------------------------------------------------
# Helper builders ------------------------------------------------------------
# ---------------------------------------------------------------------------

def _make_diagram() -> str:
    """Return an ASCII diagram that visualises top-level interactions."""
    return textwrap.dedent(
        """
        ```
        User ─▶ Frosty/Builder (ice_builder)
                    ↓ Blueprint
        MCP API     (ice_api)
                    ↓
        Orchestrator (ice_orchestrator)
                    ↓
        Client / CLI (ice_client · ice_cli)
        ```
        """
    ).strip()


def _make_layer_table() -> str:
    header = "| Layer | Responsibilities | May import from | Py modules |"
    divider = "|------|------------------|-----------------|-----------|"
    rows: List[str] = []

    for pkg, desc, imports in LAYERS:
        module_count = sum(1 for _ in (SRC_DIR / pkg).rglob("*.py"))
        rows.append(f"| **{pkg}** | {desc} | {imports} | {module_count} |")

    return "\n".join([header, divider, *rows])


def _collect_node_configs() -> Dict[str, Tuple[str, str]]:
    """Return mapping of node_type → (config_class_name, docstring_summary)."""
    mapping: Dict[str, Tuple[str, str]] = {}

    # Dynamically import the node_models module only once.
    node_models_mod = __import__("ice_core.models.node_models", fromlist=["*"])

    for _name, obj in inspect.getmembers(node_models_mod, inspect.isclass):
        if not (inspect.isclass(obj) and issubclass(obj, BaseNodeConfig)):
            continue
        if obj is BaseNodeConfig:
            continue  # skip abstract base

        node_type: str = cast(str, getattr(obj, "type", ""))
        if not node_type:
            continue  # safety: shouldn't happen but guard anyway

        doc = inspect.getdoc(obj) or ""
        summary = doc.splitlines()[0] if doc else ""
        mapping[node_type] = (obj.__name__, summary)

    return dict(sorted(mapping.items(), key=lambda kv: kv[0]))


def _make_node_table() -> str:
    mapping = _collect_node_configs()
    header = "| Node Type | Config class | Purpose |"
    divider = "|-----------|--------------|---------|"
    rows = [f"| `{nt}` | `{cls}` | {desc} |" for nt, (cls, desc) in mapping.items()]
    return "\n".join([header, divider, *rows])

# ---------------------------------------------------------------------------
# Entrypoint -----------------------------------------------------------------
# ---------------------------------------------------------------------------

def build() -> None:  # noqa: D401 – imperative mood intentional
    """Generate markdown fragment and write it to *docs/generated/architecture_auto.md*."""

    content = textwrap.dedent(
        f"""
        <!-- AUTO-GENERATED: DO NOT EDIT DIRECTLY -->
        # iceOS Architecture Overview

        ## High-level flow

        {_make_diagram()}

        ## Layer responsibilities

        {_make_layer_table()}

        ## Node types

        {_make_node_table()}
        """
    ).strip() + "\n"

    out_file = DOC_OUT_DIR / "architecture_auto.md"
    out_file.write_text(content, encoding="utf-8")
    print(f"[gen-docs] Wrote {out_file.relative_to(ROOT)}")


if __name__ == "__main__":  # pragma: no cover – script utility
    build()
