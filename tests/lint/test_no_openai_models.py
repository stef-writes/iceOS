"""Failing test if any AiNodeConfig declares an OpenAI model.

The organisation adopted DeepSeek as the default provider.  Any new AiNode
configuration must therefore use *DeepSeek* (or another non-OpenAI provider).

We introspect all Python modules under *src* and *cli_demo* looking for
AiNodeConfig instantiations and assert that the *model* argument does **not**
contain a banned pattern (gpt-3.5-turbo, gpt-4, gpt-4-turbo, gpt-4o, etc.).

This keeps the rule lightweight without introducing static-analysis deps.
"""

from __future__ import annotations

import ast
import pathlib
import re
from typing import Iterator

# Directories to scan ----------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parents[2]  # project root
SCAN_DIRS = [ROOT / "src", ROOT / "cli_demo"]

BANNED_PATTERNS = [
    re.compile(r"gpt[-_]?(?:3\.5|4|4o|4-turbo)", re.IGNORECASE),
]


class _ModelVisitor(ast.NodeVisitor):
    """Collect AiNodeConfig calls and their *model* kwarg."""

    def __init__(self) -> None:
        self.violations: list[tuple[pathlib.Path, int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: D401 override
        func_name = _name_from_node(node.func)
        if func_name.endswith("AiNodeConfig"):
            for keyword in node.keywords:
                if keyword.arg == "model":
                    value = _literal_str(keyword.value)
                    if value and any(p.search(value) for p in BANNED_PATTERNS):
                        self.violations.append((current_file, node.lineno, value))
        self.generic_visit(node)


def _name_from_node(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _literal_str(node: ast.AST) -> str | None:
    """Return the literal string value when *node* is an ast.Constant/Str."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _iter_py_files() -> Iterator[pathlib.Path]:
    for base in SCAN_DIRS:
        for py in base.rglob("*.py"):
            yield py


current_file: pathlib.Path  # global updated per-file inside loop


def test_no_openai_models():
    """Fail when any AiNodeConfig uses an OpenAI model."""
    global current_file
    visitor = _ModelVisitor()

    for path in _iter_py_files():
        current_file = path
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            # Skip files that fail to parse (unlikely in tests environment)
            continue
        visitor.visit(tree)

    if visitor.violations:
        msg_lines = [
            "The following AiNodeConfig declarations use banned OpenAI models:",
        ]
        for file_path, lineno, model_name in visitor.violations:
            rel = file_path.relative_to(ROOT)
            msg_lines.append(f"  {rel}:{lineno} – model='{model_name}'")
        raise AssertionError("\n".join(msg_lines))
