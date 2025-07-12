"""Simple guard preventing cross-layer imports.

This is **not** a full-blown import-linter replacement – it is fast enough to
run in pre-commit and CI.  When it detects a violation, it prints a readable
error and exits with status 1.
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import sys
from typing import Iterable, Sequence

# Mapping: package → set of disallowed import prefixes
_RULES = {
    "ice_sdk": {"app", "ice_orchestrator"},
    "ice_core": {"app", "ice_sdk", "ice_orchestrator"},
    # Add more as the architecture evolves
}


class _Violation(ast.NodeVisitor):
    def __init__(self, package: str, forbidden: set[str]) -> None:  # noqa: D401
        self.package = package
        self.forbidden = forbidden
        self.errors: list[str] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: D401
        if node.module is None:
            return
        head = node.module.split(".")[0]
        if head in self.forbidden:
            self.errors.append(
                f"{self.package}: disallowed import '{node.module}' at line {node.lineno}"
            )


def _scan_file(
    fp: pathlib.Path, root_package: str, disallowed: set[str]
) -> Iterable[str]:
    try:
        source = fp.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Fallback for rare encoding issues on Windows CI – skip undecodable bytes
        source = fp.read_text(encoding="utf-8", errors="ignore")  # type: ignore[call-arg] – 'errors' param only Py3.11+
    tree = ast.parse(source)
    visitor = _Violation(root_package, disallowed)
    visitor.visit(tree)
    return visitor.errors


def _iter_py_files(package_dir: pathlib.Path) -> Iterable[pathlib.Path]:  # noqa: D401
    yield from package_dir.rglob("*.py")


def check_packages(packages: Sequence[str]) -> int:  # noqa: D401
    base_dir = pathlib.Path(__file__).resolve().parent.parent / "src"
    failures = 0
    for pkg in packages:
        forbidden = _RULES.get(pkg, set())
        package_dir = base_dir / pkg.replace(".", "/")
        for file in _iter_py_files(package_dir):
            failures += len(list(_scan_file(file, pkg, forbidden)))
    return failures


def main() -> None:  # noqa: D401
    parser = argparse.ArgumentParser(description="check cross layer imports")
    parser.add_argument("packages", nargs="*", default=list(_RULES))
    args = parser.parse_args()
    failures = check_packages(args.packages)
    if failures:
        print(f"Layer guard: {failures} violation(s) found.")
        sys.exit(1)
    print("Layer guard: all good.")


if __name__ == "__main__":  # pragma: no cover
    main()
