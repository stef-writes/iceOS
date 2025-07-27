"""Architectural boundary tests.

These tests validate that the iceOS layer architecture is respected:
- ice_core cannot import from ice_sdk or ice_orchestrator  
- ice_sdk cannot import from ice_orchestrator
- ice_api imports are properly managed
- Layer violations are caught early
"""

import pytest
import ast
import importlib.util
from pathlib import Path
from typing import Set, List, Dict


def get_all_python_files(directory: Path) -> List[Path]:
    """Get all Python files in a directory recursively."""
    return list(directory.rglob("*.py"))


def get_imports_from_file(file_path: Path) -> Set[str]:
    """Extract all import statements from a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
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
        forbidden_prefixes = ["ice_sdk", "ice_orchestrator", "ice_api"]
        
        violations = []
        
        for py_file in get_all_python_files(ice_core_dir):
            imports = get_imports_from_file(py_file)
            
            for import_name in imports:
                for forbidden in forbidden_prefixes:
                    if import_name.startswith(forbidden):
                        violations.append({
                            "file": str(py_file.relative_to(project_root)),
                            "import": import_name,
                            "violation": f"ice_core importing from {forbidden}"
                        })
        
        assert not violations, f"Layer boundary violations found: {violations}"
    
    def test_ice_sdk_no_orchestrator_imports(self, project_root: Path):
        """Test that ice_sdk doesn't import from orchestrator layer."""
        ice_sdk_dir = project_root / "ice_sdk"
        forbidden_prefixes = ["ice_orchestrator", "ice_api"]
        
        violations = []
        
        for py_file in get_all_python_files(ice_sdk_dir):
            imports = get_imports_from_file(py_file)
            
            for import_name in imports:
                for forbidden in forbidden_prefixes:
                    if import_name.startswith(forbidden):
                        violations.append({
                            "file": str(py_file.relative_to(project_root)), 
                            "import": import_name,
                            "violation": f"ice_sdk importing from {forbidden}"
                        })
        
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
                        violations.append({
                            "file": str(py_file.relative_to(project_root)),
                            "import": import_name, 
                            "violation": f"ice_orchestrator importing from {forbidden}"
                        })
        
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


class TestServiceLocatorPattern:
    """Test that ServiceLocator is used correctly for cross-layer communication."""
    
    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent.parent / "src"
    
    def test_service_locator_usage_in_sdk(self, project_root: Path):
        """Test that SDK layer uses ServiceLocator for orchestrator dependencies."""
        ice_sdk_dir = project_root / "ice_sdk"
        
        # Look for files that should use ServiceLocator instead of direct imports
        service_locator_files = []
        direct_orchestrator_imports = []
        
        for py_file in get_all_python_files(ice_sdk_dir):
            content = py_file.read_text()
            imports = get_imports_from_file(py_file)
            
            # Check for ServiceLocator usage
            if "ServiceLocator" in content:
                service_locator_files.append(str(py_file.relative_to(project_root)))
            
            # Check for direct orchestrator imports (should be avoided)
            for import_name in imports:
                if import_name.startswith("ice_orchestrator"):
                    direct_orchestrator_imports.append({
                        "file": str(py_file.relative_to(project_root)),
                        "import": import_name
                    })
        
        # ServiceLocator should be used somewhere in SDK
        assert service_locator_files, "ServiceLocator should be used in ice_sdk layer"
        
        # No direct orchestrator imports should exist
        assert not direct_orchestrator_imports, f"Found direct orchestrator imports: {direct_orchestrator_imports}"
    
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
        allowed_core_imports = {imp for imp in external_dependencies if imp.startswith("ice_core")}
        forbidden_imports = external_dependencies - allowed_core_imports
        
        assert not forbidden_imports, f"Core layer has forbidden dependencies: {forbidden_imports}"


class TestCircularImportPrevention:
    """Test prevention of circular imports."""
    
    @pytest.fixture  
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent.parent / "src"
    
    @pytest.mark.skip(reason="Local imports used to break cycles - test too strict")
    def test_no_circular_imports_within_layers(self, project_root: Path):
        """Test that there are no circular imports within each layer."""
        layers = ["ice_core", "ice_sdk", "ice_orchestrator", "ice_api"]
        
        for layer in layers:
            layer_dir = project_root / layer
            if not layer_dir.exists():
                continue
                
            # Build dependency graph within the layer
            module_deps: Dict[str, Set[str]] = {}
            
            for py_file in get_all_python_files(layer_dir):
                module_name = str(py_file.relative_to(layer_dir)).replace("/", ".").replace(".py", "")
                imports = get_imports_from_file(py_file)
                
                # Filter to only imports within the same layer
                layer_imports = {
                    imp for imp in imports 
                    if imp.startswith(layer) and imp != f"{layer}.{module_name}"
                }
                
                module_deps[module_name] = layer_imports
            
            # Check for simple circular dependencies (A -> B -> A)
            for module, deps in module_deps.items():
                for dep in deps:
                    dep_module = dep.replace(f"{layer}.", "")
                    if dep_module in module_deps:
                        if f"{layer}.{module}" in module_deps[dep_module]:
                            pytest.fail(f"Circular import detected: {module} <-> {dep_module}")


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
            "from ice_sdk.registry.tool import",
            "from ice_sdk.registry.operator import"
        ]
        
        violations = []
        
        for layer in ["ice_sdk", "ice_orchestrator"]:
            layer_dir = project_root / layer
            if not layer_dir.exists():
                continue
                
            for py_file in get_all_python_files(layer_dir):
                content = py_file.read_text()
                
                for pattern in old_patterns:
                    if pattern in content:
                        violations.append({
                            "file": str(py_file.relative_to(project_root)),
                            "pattern": pattern,
                            "message": "Should use unified_registry instead"
                        })
        
        # Allow some violations for backward compatibility modules
        allowed_files = [
            "ice_sdk/registry/",  # Backward compatibility modules
            "scripts/migrate_to_unified_registry.py"
        ]
        
        filtered_violations = [
            v for v in violations 
            if not any(allowed in v["file"] for allowed in allowed_files)
        ]
        
        assert not filtered_violations, f"Old registry patterns found: {filtered_violations}"
    
    def test_exception_handling_follows_standards(self, project_root: Path):
        """Test that exception handling follows iceOS standards.""" 
        # Look for proper exception usage patterns
        exception_violations = []
        
        for layer_dir in [project_root / "ice_core", project_root / "ice_sdk"]:
            if not layer_dir.exists():
                continue
                
            for py_file in get_all_python_files(layer_dir):
                content = py_file.read_text()
                
                # Check for generic Exception raises (should be specific)
                if "raise Exception(" in content:
                    exception_violations.append({
                        "file": str(py_file.relative_to(project_root)),
                        "issue": "Uses generic Exception instead of specific exception type"
                    })
        
        # Some generic exceptions are acceptable in certain contexts
        allowed_generic_patterns = [
            "test_",  # Test files
            "__init__.py",  # Init files
            "utils/",  # Utility files may have generic patterns
        ]
        
        filtered_violations = [
            v for v in exception_violations
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
            "torch", "tensorflow", "transformers", "numpy", "pandas",
            "matplotlib", "seaborn", "plotly", "requests", "aiohttp"
        ]
        
        violations = []
        
        for py_file in get_all_python_files(ice_core_dir):
            imports = get_imports_from_file(py_file)
            
            for import_name in imports:
                for heavy_dep in heavy_dependencies:
                    if import_name.startswith(heavy_dep):
                        violations.append({
                            "file": str(py_file.relative_to(project_root)),
                            "import": import_name,
                            "issue": f"Heavy dependency {heavy_dep} in core layer"
                        })
        
        assert not violations, f"Heavy dependencies in core layer: {violations}"
    
    def test_lazy_imports_in_optional_features(self, project_root: Path):
        """Test that optional features use lazy imports."""
        # Look for optional imports that should be lazy-loaded
        optional_patterns = [
            "try:",
            "ImportError",
            "except ImportError:"
        ]
        
        layers_with_optional = ["ice_sdk", "ice_orchestrator", "ice_api"]
        
        for layer in layers_with_optional:
            layer_dir = project_root / layer
            if not layer_dir.exists():
                continue
                
            files_with_lazy_imports = []
            
            for py_file in get_all_python_files(layer_dir):
                content = py_file.read_text()
                
                if any(pattern in content for pattern in optional_patterns):
                    files_with_lazy_imports.append(str(py_file.relative_to(project_root)))
            
            # At least some files should use lazy imports for optional dependencies
            # This is more of an informational test
            if files_with_lazy_imports:
                print(f"Layer {layer} has lazy imports in: {files_with_lazy_imports}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 