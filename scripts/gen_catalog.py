#!/usr/bin/env python3
"""Generate a JSON catalog of Nodes/Tools/Agents/Chains defined in *src/*.

Lifted from the prior ``dev_tools/legacy`` location so that build tooling and
external callers can rely on ``scripts/gen_catalog.py`` directly.
"""
from __future__ import annotations

import ast
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Literal, Optional

from pydantic import BaseModel

SEARCH_ROOTS: tuple[str, ...] = ("src",)
SUFFIX_KIND_MAP: dict[str, str] = {
    "Node": "node",
    "Tool": "tool",
    "Agent": "agent",
    "Chain": "chain",
}
OUTPUT_FILE = Path("docs") / "capability_catalog.json"

KindLiteral = Literal["node", "tool", "agent", "chain"]


class Capability(BaseModel):
    id: str
    kind: KindLiteral
    path: str


class Catalog(BaseModel):
    generated_at: datetime
    capabilities: List[Capability]


def discover_py_files() -> Iterable[Path]:
    for root in SEARCH_ROOTS:
        for path in Path(root).rglob("*.py"):
            if any(part.startswith("__pycache__") for part in path.parts):
                continue
            yield path


def guess_kind(class_name: str) -> Optional[KindLiteral]:
    for suffix, kind in SUFFIX_KIND_MAP.items():
        if class_name.endswith(suffix):
            return kind  # type: ignore[return-value]
    return None


class _ClassCollector(ast.NodeVisitor):
    def __init__(self):
        self.definitions: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        self.definitions.append(node.name)


def analyse_file(path: Path, project_root: Path) -> list[Capability]:
    rel_path = path.resolve().relative_to(project_root).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    coll = _ClassCollector()
    coll.visit(tree)
    module_qual = rel_path[:-3].replace("/", ".")

    caps: list[Capability] = []
    for cls in coll.definitions:
        kind = guess_kind(cls)
        if kind:
            caps.append(Capability(id=f"{module_qual}.{cls}", kind=kind, path=rel_path))
    return caps


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    all_caps: list[Capability] = []
    for py_file in discover_py_files():
        all_caps.extend(analyse_file(py_file, project_root))
    all_caps.sort(key=lambda c: c.id)
    catalog = Catalog(generated_at=datetime.utcfromtimestamp(0), capabilities=all_caps)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        catalog.model_dump_json(indent=2, exclude={"generated_at"}) + "\n"
    )
    print(f"[scripts.gen_catalog] wrote {len(all_caps)} entries", file=sys.stderr)


if __name__ == "__main__":
    main()
