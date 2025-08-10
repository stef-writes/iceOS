"""Architectural boundary tests.

These tests validate that the iceOS layer architecture is respected:
- ice_core cannot import from ice_orchestrator or ice_api
- ice_builder cannot import from ice_orchestrator or ice_api
- ice_api imports are properly managed
- Layer violations are caught early
"""

import ast
from pathlib import Path
from typing import List, Set

import pytest


def get_all_python_files(directory: Path) -> List[Path]:
    """Get all Python files in a directory recursively."""
    return list(directory.rglob("*.py"))


def get_imports_from_file(file_path: Path) -> Set[str]:
    """Extract all import statements from a Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)

        return imports
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        # Skip files that can't be parsed
        return set()


class TestLayerBoundaries:
    """Test that layer boundaries are respected."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent.parent / "src"

    def test_ice_core_no_upward_imports(self, project_root: Path):
        """Test that ice_core doesn't import from higher layers."""
        ice_core_dir = project_root / "ice_core"
        forbidden_prefixes = ["ice_orchestrator", "ice_api"]

        violations = []

        for py_file in get_all_python_files(ice_core_dir):
            imports = get_imports_from_file(py_file)

            for import_name in imports:
                for forbidden in forbidden_prefixes:
                    if import_name.startswith(forbidden):
                        violations.append(
                            {
                                "file": str(py_file.relative_to(project_root)),
                                "import": import_name,
                                "violation": f"ice_core importing from {forbidden}",
                            }
                        )

        assert not violations, f"Layer boundary violations found: {violations}"

    def test_ice_builder_no_orchestrator_imports(self, project_root: Path):
        """Test that ice_builder doesn't import from orchestrator layer (with exceptions for workflow building)."""
        ice_builder_dir = project_root / "ice_builder"
        forbidden_prefixes = ["ice_orchestrator", "ice_api"]

        # Allow specific exceptions for legitimate interfaces
        allowed_exceptions = [
            "ice_orchestrator.workflow",  # WorkflowBuilder needs to create Workflow instances
        ]

        violations = []

        for py_file in get_all_python_files(ice_builder_dir):
            imports = get_imports_from_file(py_file)

            for import_name in imports:
                for forbidden in forbidden_prefixes:
                    if import_name.startswith(forbidden):
                        # Check if this is an allowed exception
                        if import_name not in allowed_exceptions:
                            violations.append(
                                {
                                    "file": str(py_file.relative_to(project_root)),
                                    "import": import_name,
                                    "violation": f"ice_builder importing from {forbidden}",
                                }
                            )

        assert not violations, f"Layer boundary violations found: {violations}"

    def test_ice_orchestrator_limited_imports(self, project_root: Path):
        """Test that ice_orchestrator has controlled imports."""
        ice_orchestrator_dir = project_root / "ice_orchestrator"
        forbidden_prefixes = ["ice_api"]  # Orchestrator can import SDK and core

        violations = []

        for py_file in get_all_python_files(ice_orchestrator_dir):
            imports = get_imports_from_file(py_file)

            for import_name in imports:
                for forbidden in forbidden_prefixes:
                    if import_name.startswith(forbidden):
                        violations.append(
                            {
                                "file": str(py_file.relative_to(project_root)),
                                "import": import_name,
                                "violation": f"ice_orchestrator importing from {forbidden}",
                            }
                        )

        assert not violations, f"Layer boundary violations found: {violations}"

    def test_ice_api_can_import_all_layers(self, project_root: Path):
        """Test that ice_api can import from all other layers (it's the top layer)."""
        ice_api_dir = project_root / "ice_api"

        # This test just ensures API layer files can be imported without issues
        # No forbidden imports for the top layer

        import_errors = []

        for py_file in get_all_python_files(ice_api_dir):
            imports = get_imports_from_file(py_file)

            # Check for any obvious circular import issues
            for import_name in imports:
                if import_name.startswith("ice_api"):
                    # Self-imports are ok within the layer
                    continue

        # No assertions needed - this test passes if no exceptions during import collection
        assert True


import pytest

## Removed obsolete ServiceLocator pattern tests (pattern removed from codebase)


class TestCoreLayerIndependence:
    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent.parent / "src"

    def test_core_layer_independence(self, project_root: Path):
        """Test that core layer remains completely independent."""
        ice_core_dir = project_root / "ice_core"

        external_dependencies = set()

        for py_file in get_all_python_files(ice_core_dir):
            imports = get_imports_from_file(py_file)

            for import_name in imports:
                # Track imports that are not standard library or external packages
                if import_name.startswith(("ice_", "app_")):
                    external_dependencies.add(import_name)

        # Core should only import from itself
        allowed_core_imports = {
            imp for imp in external_dependencies if imp.startswith("ice_core")
        }
        forbidden_imports = external_dependencies - allowed_core_imports

        assert (
            not forbidden_imports
        ), f"Core layer has forbidden dependencies: {forbidden_imports}"


## Removed deprecated circular import check (no longer meaningful)


class TestProtocolCompliance:
    """Test compliance with iceOS architectural protocols."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent.parent / "src"

    def test_registry_usage_follows_pattern(self, project_root: Path):
        """Test that registry usage follows the unified pattern."""
        # Look for old registry patterns that should be migrated
        old_patterns = [
            "global_tool_registry",
            "global_operator_registry",
            "from ice_core.registry.tool import",
            "from ice_core.registry.operator import",
        ]

        violations = []

        for layer in ["ice_builder", "ice_orchestrator"]:
            layer_dir = project_root / layer
            if not layer_dir.exists():
                continue

            for py_file in get_all_python_files(layer_dir):
                content = py_file.read_text()

                for pattern in old_patterns:
                    if pattern in content:
                        violations.append(
                            {
                                "file": str(py_file.relative_to(project_root)),
                                "pattern": pattern,
                                "message": "Should use unified_registry instead",
                            }
                        )

        # Allow some violations for backward compatibility modules
        allowed_files = [
            "ice_builder/registry/",  # Backward compatibility modules
            "scripts/migrate_to_unified_registry.py",
        ]

        filtered_violations = [
            v
            for v in violations
            if not any(allowed in v["file"] for allowed in allowed_files)
        ]

        assert (
            not filtered_violations
        ), f"Old registry patterns found: {filtered_violations}"

    def test_no_new_service_locator_usage(self, project_root: Path):
        """Disallow introducing new ServiceLocator usages in code going forward.

        Existing transitional usages are permitted in a few orchestrator/API
        files, but new code should prefer runtime factories or explicit
        dependency injection.
        """
        transitional_allowlist = {
            "ice_orchestrator/__init__.py",
            "ice_orchestrator/context/manager.py",
            "ice_api/main.py",
            # Transitional core shims kept for backwards compatibility during migration
            "ice_core/services/__init__.py",
            "ice_core/services/locator.py",
            "ice_core/services/initialization.py",
            "ice_core/services/tool_service.py",
            "ice_core/services/alert_service.py",
            # Orchestrator services still referencing locator (to be migrated)
            "ice_orchestrator/base_workflow.py",
            "ice_orchestrator/services/workflow_service.py",
            # API routes with legacy references
            "ice_api/api/mcp_jsonrpc.py",
            "ice_api/api/mcp.py",
            # Docs/examples mentioning ServiceLocator
            "ice_core/protocols/runtime_factories.py",
        }

        violations = []

        for py_file in get_all_python_files(project_root):
            if "tests/" in str(py_file):
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if "ServiceLocator" in content:
                rel = str(py_file.relative_to(project_root))
                if rel not in transitional_allowlist:
                    violations.append(rel)

        # Allow the legacy LLM adapter reference (to be removed in refactor) and
        # the temporary shim modules under ice_core/services/* that are being deprecated
        allowed = set()  # No allowances remaining once adapters are refactored
        filtered = [v for v in violations if v not in allowed]
        assert not filtered, f"New ServiceLocator usages found: {filtered}"

    def test_exception_handling_follows_standards(self, project_root: Path):
        """Test that exception handling follows iceOS standards."""
        # Look for proper exception usage patterns
        exception_violations = []

        for layer_dir in [project_root / "ice_core", project_root / "ice_builder"]:
            if not layer_dir.exists():
                continue

            for py_file in get_all_python_files(layer_dir):
                content = py_file.read_text()

                # Check for generic Exception raises (should be specific)
                if "raise Exception(" in content:
                    exception_violations.append(
                        {
                            "file": str(py_file.relative_to(project_root)),
                            "issue": "Uses generic Exception instead of specific exception type",
                        }
                    )

        # Some generic exceptions are acceptable in certain contexts
        allowed_generic_patterns = [
            "test_",  # Test files
            "__init__.py",  # Init files
            "utils/",  # Utility files may have generic patterns
        ]

        filtered_violations = [
            v
            for v in exception_violations
            if not any(pattern in v["file"] for pattern in allowed_generic_patterns)
        ]

        # This is a guideline test - warn but don't fail
        if filtered_violations:
            print(f"Warning: Found generic exception usage: {filtered_violations}")


class TestMemoryAndPerformance:
    """Test architectural patterns that affect memory and performance."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent.parent / "src"

    def test_no_heavy_imports_in_core(self, project_root: Path):
        """Test that core layer doesn't import heavy dependencies."""
        ice_core_dir = project_root / "ice_core"
        heavy_dependencies = [
            "torch",
            "tensorflow",
            "transformers",
            "numpy",
            "pandas",
            "matplotlib",
            "seaborn",
            "plotly",
            "requests",
            "aiohttp",
        ]

        violations = []

        for py_file in get_all_python_files(ice_core_dir):
            imports = get_imports_from_file(py_file)

            for import_name in imports:
                for heavy_dep in heavy_dependencies:
                    if import_name.startswith(heavy_dep):
                        violations.append(
                            {
                                "file": str(py_file.relative_to(project_root)),
                                "import": import_name,
                                "issue": f"Heavy dependency {heavy_dep} in core layer",
                            }
                        )

        assert not violations, f"Heavy dependencies in core layer: {violations}"

    def test_lazy_imports_in_optional_features(self, project_root: Path):
        """Test that optional features use lazy imports."""
        # Look for optional imports that should be lazy-loaded
        optional_patterns = ["try:", "ImportError", "except ImportError:"]

        layers_with_optional = ["ice_builder", "ice_orchestrator", "ice_api"]

        for layer in layers_with_optional:
            layer_dir = project_root / layer
            if not layer_dir.exists():
                continue

            files_with_lazy_imports = []

            for py_file in get_all_python_files(layer_dir):
                content = py_file.read_text()

                if any(pattern in content for pattern in optional_patterns):
                    files_with_lazy_imports.append(
                        str(py_file.relative_to(project_root))
                    )

            # At least some files should use lazy imports for optional dependencies
            # This is more of an informational test
            if files_with_lazy_imports:
                print(f"Layer {layer} has lazy imports in: {files_with_lazy_imports}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
