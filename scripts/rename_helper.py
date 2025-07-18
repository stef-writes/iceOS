"""AST codemod to migrate legacy IceOS vocabulary to v2 terminology.

Usage (from repo root)
----------------------
$ python scripts/rename_helper.py src/ tests/

The helper is intentionally **idempotent** – running it multiple times does
not change files that already use the new names.

Only Python files are modified; literal strings, comments and YAML/JSON are
left untouched.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import libcst as cst
from libcst import matchers as m
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand, parallel_exec_transform_with_prettyprint

# ---------------------------------------------------------------------------
# Mapping – legacy → new terminology  ---------------------------------------
# ---------------------------------------------------------------------------
_SYMBOL_MAP: Mapping[str, str] = {
    "AiNodeConfig": "LLMOperatorConfig",
    "ToolNodeConfig": "SkillNodeConfig",
    "BaseTool": "SkillBase",
    "ToolError": "SkillExecutionError",  # opportunistic swap
}


class RenameIdentifiersCommand(VisitorBasedCodemodCommand):
    """LibCST codemod that renames legacy identifiers to the new vocabulary.

    It rewrites:
        * import statements (both `import X` & `from mod import X`)
        * standalone identifier usages (Name nodes)

    Attribute names (e.g. obj.BaseTool) are left unchanged because runtime
    aliases ensure backward-compat; touching them risks false positives.
    """

    DESCRIPTION: str = (
        "Replace AiNodeConfig → LLMOperatorConfig, ToolNodeConfig → SkillNodeConfig, "
        "BaseTool → SkillBase across the codebase."
    )

    def __init__(self, context: CodemodContext) -> None:  # noqa: D401
        super().__init__(context)
        # Pre-convert for quick membership checks
        self._old_symbols: set[str] = set(_SYMBOL_MAP.keys())

    # ------------------------------------------------------------------
    # Import renames
    # ------------------------------------------------------------------

    def leave_ImportAlias(  # noqa: D401 – LibCST override
        self, original_node: cst.ImportAlias, updated_node: cst.ImportAlias
    ) -> cst.ImportAlias:
        name_val = updated_node.name.value
        if name_val in _SYMBOL_MAP:
            return updated_node.with_changes(name=cst.Name(_SYMBOL_MAP[name_val]))
        return updated_node

    # ------------------------------------------------------------------
    # Identifier renames (standalone Name nodes)
    # ------------------------------------------------------------------

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.BaseExpression:  # noqa: D401
        if original_node.value in _SYMBOL_MAP:
            return updated_node.with_changes(value=_SYMBOL_MAP[original_node.value])
        return updated_node

    # ------------------------------------------------------------------
    # Selective traversal optimisation – skip YAML/JSON directories
    # ------------------------------------------------------------------

    @staticmethod
    def should_skip_file(path: Path) -> bool:  # noqa: D401
        return path.suffix.lower() != ".py"


# ---------------------------------------------------------------------------
# CLI driver
# ---------------------------------------------------------------------------

def _iter_py_files(paths: Sequence[str]) -> Iterable[Path]:  # noqa: D401
    for p in map(Path, paths):
        if p.is_dir():
            yield from (f for f in p.rglob("*.py") if f.is_file())
        elif p.is_file() and p.suffix == ".py":
            yield p


def main() -> None:  # noqa: D401
    parser = argparse.ArgumentParser(description="IceOS vocab migration codemod")
    parser.add_argument(
        "paths",
        nargs="+",
        help="One or more files/directories to transform (recursively searches *.py)",
    )
    args = parser.parse_args()

    targets = [str(p) for p in _iter_py_files(args.paths)]
    if not targets:
        print("No Python files found in provided paths.")
        return

    # Run in parallel using LibCST helper (context is auto-created) ----------
    parallel_exec_transform_with_prettyprint(RenameIdentifiersCommand, targets)


if __name__ == "__main__":  # pragma: no cover
    main() 