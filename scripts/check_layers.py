"""Guard preventing cross-layer imports and architectural violations.

This checks:
1. Cross-layer imports (original functionality)
2. Dynamic imports (importlib, __import__, eval, exec) outside allowlist
3. ServiceLocator usage outside allowed layers
4. Direct unified_registry imports outside allowed layers
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Allowed cross-service dependencies (single source of truth) ----------------
# ---------------------------------------------------------------------------
# Key   = service owning the *calling* file  (src/<service>/...)
# Value = list of other top-level services it may import from.
# If a service is *absent* from the map we assume **no** external imports.
# ---------------------------------------------------------------------------

ALLOWED_DEPENDENCIES: dict[str, list[str]] = {
    "ice_cli": [
        "ice_core",
        "ice_client",
        "ice_orchestrator",
    ],  # CLI needs client for remote, orchestrator for local
    "ice_api": ["ice_core", "ice_orchestrator"],  # API delegates to orchestrator
    "ice_client": ["ice_core"],  # Client only needs core models
    "ice_builder": ["ice_core"],  # Builder creates structures using core models
    "ice_orchestrator": [
        "ice_core",
        "ice_tools",
    ],  # Runtime depends on core and built-in tools
    "ice_tools": ["ice_core"],  # Built-in tools depend only on core
    "frosty": ["ice_core", "ice_builder"],  # CLI only
    "frosty.core": ["ice_core", "ice_builder"],
    "frosty.codegen": ["ice_core", "ice_builder"],
    "ice_core": [],  # Foundation layer - no external dependencies
}

# ---------------------------------------------------------------------------
# Dynamic import allowlist --------------------------------------------------
# ---------------------------------------------------------------------------
# Files allowed to use dynamic imports (full path relative to src/)
DYNAMIC_IMPORT_ALLOWLIST = {
    "ice_orchestrator/execution/wasm_executor.py",  # Sandbox needs runtime import control
    "ice_core/plugins/discovery.py",  # Plugin system requires dynamic loading
    "ice_core/unified_registry.py",  # Registry loads modules dynamically
    "ice_core/llm/providers/__init__.py",  # Provider discovery
    "ice_orchestrator/execution/executors/__init__.py",  # Executor loading
    "ice_api/main.py",  # Startup initialization
    "ice_api/mcp_stdio_server.py",  # Alternative startup
    "ice_api/startup_utils.py",  # Helper for dynamic loading
    "ice_orchestrator/__init__.py",  # Layer initialization
    "ice_orchestrator/services/network_coordinator.py",  # Network loading
    "ice_api/api/mcp.py",  # Component validation requires exec() for dynamic tools
}

# Layers allowed to use ServiceLocator.get()
SERVICE_LOCATOR_ALLOWED_LAYERS = {"ice_api", "ice_orchestrator"}

# Layers allowed to import unified_registry directly
REGISTRY_ALLOWED_LAYERS = {"ice_orchestrator", "ice_tools", "ice_core"}

# ---------------------------------------------------------------------------
# Violation collectors ------------------------------------------------------
# ---------------------------------------------------------------------------


class ViolationCollector:
    """Collects and reports architectural violations."""

    def __init__(self):
        self.cross_layer_violations: List[Tuple[Path, str, List[str]]] = []
        self.dynamic_import_violations: List[Tuple[Path, int, str]] = []
        self.service_locator_violations: List[Tuple[Path, int]] = []
        self.registry_violations: List[Tuple[Path, int]] = []

    @property
    def total_violations(self) -> int:
        return (
            len(self.cross_layer_violations)
            + len(self.dynamic_import_violations)
            + len(self.service_locator_violations)
            + len(self.registry_violations)
        )

    def report(self) -> None:
        """Print all violations to stdout."""
        if self.cross_layer_violations:
            print("\n=== CROSS-LAYER IMPORT VIOLATIONS ===")
            for path, imported, allowed in self.cross_layer_violations:
                print(f"{path}: imports {imported} (allowed: {allowed or 'none'})")

        if self.dynamic_import_violations:
            print("\n=== DYNAMIC IMPORT VIOLATIONS ===")
            for path, line, pattern in self.dynamic_import_violations:
                print(f"{path}:{line}: {pattern}")

        if self.service_locator_violations:
            print("\n=== SERVICE LOCATOR VIOLATIONS ===")
            for path, line in self.service_locator_violations:
                print(f"{path}:{line}: ServiceLocator.get() outside allowed layers")

        if self.registry_violations:
            print("\n=== REGISTRY IMPORT VIOLATIONS ===")
            for path, line in self.registry_violations:
                print(f"{path}:{line}: unified_registry import outside allowed layers")

        if self.total_violations:
            print(f"\nTotal violations: {self.total_violations}")


# ---------------------------------------------------------------------------
# Core validators -----------------------------------------------------------
# ---------------------------------------------------------------------------


def check_cross_layer_imports(
    py_file: Path, current_service: str, collector: ViolationCollector
) -> None:
    """Check for forbidden cross-layer imports."""
    allowed = ALLOWED_DEPENDENCIES.get(current_service, [])

    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        print(f"Syntax error while parsing {py_file}: {exc}")
        return

    for node in ast.walk(tree):
        imported_root: str | None = None

        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_root = alias.name.split(".")[0]
                if _is_forbidden(imported_root, current_service, allowed):
                    collector.cross_layer_violations.append(
                        (py_file, imported_root, allowed)
                    )

        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            imported_root = node.module.split(".")[0]
            if _is_forbidden(imported_root, current_service, allowed):
                collector.cross_layer_violations.append(
                    (py_file, imported_root, allowed)
                )


def check_dynamic_imports(
    py_file: Path, current_service: str, collector: ViolationCollector
) -> None:
    """Check for dynamic imports outside allowlist."""
    # Skip if file is in allowlist
    src_root = Path(__file__).resolve().parent.parent / "src"
    relative_path = py_file.relative_to(src_root)
    if str(relative_path) in DYNAMIC_IMPORT_ALLOWLIST:
        return

    content = py_file.read_text(encoding="utf-8")

    # Patterns to detect
    patterns = [
        (r"importlib\.import_module\s*\(", "importlib.import_module()"),
        (r"__import__\s*\(", "__import__()"),
        (r"\beval\s*\(", "eval()"),
        (r"\bexec\s*\(", "exec()"),
    ]

    for pattern, name in patterns:
        for match in re.finditer(pattern, content):
            line_num = content[: match.start()].count("\n") + 1
            collector.dynamic_import_violations.append((py_file, line_num, name))


def check_service_locator(
    py_file: Path, current_service: str, collector: ViolationCollector
) -> None:
    """Check for ServiceLocator.get() outside allowed layers."""
    if current_service in SERVICE_LOCATOR_ALLOWED_LAYERS:
        return

    content = py_file.read_text(encoding="utf-8")
    pattern = r"ServiceLocator\.get\s*\("

    for match in re.finditer(pattern, content):
        line_num = content[: match.start()].count("\n") + 1
        collector.service_locator_violations.append((py_file, line_num))


def check_registry_imports(
    py_file: Path, current_service: str, collector: ViolationCollector
) -> None:
    """Check for unified_registry imports outside allowed layers."""
    if current_service in REGISTRY_ALLOWED_LAYERS:
        return

    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "unified_registry" in node.module:
                collector.registry_violations.append((py_file, node.lineno))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if "unified_registry" in alias.name:
                    collector.registry_violations.append((py_file, node.lineno))


def _is_forbidden(imported_root: str, current_service: str, allowed: list[str]) -> bool:
    """Return True if *imported_root* is a *service* outside the allowed list."""
    if not imported_root.startswith("ice_"):
        return False  # We only care about cross-service imports
    if imported_root == current_service:
        return False  # Self-import – always OK
    return imported_root not in allowed


def validate_all() -> ViolationCollector:
    """Run all validations and return collector with violations."""
    collector = ViolationCollector()
    src_root = Path(__file__).resolve().parent.parent / "src"

    for py_file in src_root.rglob("*.py"):
        # Determine the declaring service (e.g. src/ice_sdk/… -> ice_sdk)
        try:
            current_service = py_file.relative_to(src_root).parts[0]
        except (ValueError, IndexError):
            continue

        # Run all checks
        check_cross_layer_imports(py_file, current_service, collector)
        check_dynamic_imports(py_file, current_service, collector)
        check_service_locator(py_file, current_service, collector)
        check_registry_imports(py_file, current_service, collector)

    return collector


# ---------------------------------------------------------------------------
# CLI entry-point -----------------------------------------------------------
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry-point for the layer checker."""
    parser = argparse.ArgumentParser(
        description="Validate cross-layer imports and architectural boundaries"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error on any violation (default).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output violations as JSON (future feature).",
    )

    args = parser.parse_args()

    collector = validate_all()

    if collector.total_violations == 0:
        print("Layer guard: all good.")
        sys.exit(0)

    # Report violations
    collector.report()
    print(f"\nLayer guard: {collector.total_violations} violation(s) detected.")
    sys.exit(1)


if __name__ == "__main__":
    main()
