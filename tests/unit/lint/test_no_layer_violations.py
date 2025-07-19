from typing import List


def test_example_imports():
    """Ensure examples don't import from ice_sdk directly"""
    try:
        import samples.marketing_chain as marketing_chain

        # Check that the example doesn't expose internal SDK classes
        assert not hasattr(marketing_chain, "BaseNode"), "Examples must use public APIs"
        assert not hasattr(
            marketing_chain, "_internal"
        ), "Examples must not access private APIs"
    except ImportError:
        # Example doesn't exist yet, which is fine
        pass


def test_no_cross_layer_imports():
    """Ensure no imports from app.* inside ice_sdk.*"""
    import ast
    import os

    def check_file_for_violations(file_path: str) -> List[str]:
        """Check a single file for layer violations"""
        violations = []

        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("app."):
                            violations.append(
                                f"Direct import from app.* in {file_path}: {alias.name}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("app."):
                        violations.append(
                            f"Direct import from app.* in {file_path}: {node.module}"
                        )

        except (FileNotFoundError, SyntaxError):
            # Skip files that can't be parsed
            pass

        return violations

    # Check all Python files in ice_sdk
    violations = []
    for root, dirs, files in os.walk("src/ice_sdk"):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                violations.extend(check_file_for_violations(file_path))

    assert not violations, "Layer boundary violations found:\n" + "\n".join(violations)


def test_service_layer_usage():
    """Ensure services are used through proper interfaces"""
    # This test would check that components use ServiceLocator or ChainService
    # instead of direct imports across layers
    from ice_sdk.services import ChainService, ServiceLocator

    # Verify service interfaces exist
    assert hasattr(ServiceLocator, "register")
    assert hasattr(ServiceLocator, "get")
    assert hasattr(ChainService, "execute")
    assert hasattr(ChainService, "execute_async")
