import importlib

import pytest


@pytest.mark.parametrize("shim", ["ice_tools", "ice_agents"])
def test_shim_removed(shim):
    """Importing removed compatibility shims must raise ImportError."""
    with pytest.raises(ImportError):
        importlib.import_module(shim) 