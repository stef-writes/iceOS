import importlib

import pytest


@pytest.mark.parametrize(
    "shim",
    [
        "ice_agents",  # legacy agent package
        "ice_sdk.tools.hosted",  # removed tool shim
        "ice_sdk.tools.webhook",  # removed tool shim
        "ice_sdk.tools.mcp_tool",  # removed tool shim
    ],
)
def test_shim_removed(shim):
    """Importing removed compatibility shims must raise ImportError."""
    with pytest.raises(ImportError):
        importlib.import_module(shim)
