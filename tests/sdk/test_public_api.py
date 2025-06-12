"""Ensure that the officially supported public API of *ice_sdk* remains stable.

If a symbol is renamed or removed, this test will fail, prompting a conscious
semver decision (major version bump or adding a deprecation shim).
"""

import importlib

import pytest

# ---------------------------------------------------------------------------
# Update this list deliberately when you *intend* to change the public API.
# ---------------------------------------------------------------------------
PUBLIC_API = {
    "BaseNode",
    "BaseTool",
    "ToolService",
    # Data models
    "NodeConfig",
    "NodeExecutionResult",
    "NodeMetadata",
    "LLMConfig",
    "MessageTemplate",
    # Context abstraction
    "GraphContextManager",
}


@pytest.mark.parametrize("symbol", sorted(PUBLIC_API))
def test_symbol_exists(symbol):
    sdk = importlib.import_module("ice_sdk")
    assert symbol in sdk.__all__, f"{symbol} missing from __all__"
    assert hasattr(sdk, symbol), f"{symbol} not accessible as attribute"


def test_no_unexpected_exports():
    sdk = importlib.import_module("ice_sdk")
    assert set(sdk.__all__) == PUBLIC_API, "__all__ diverged from contract" 