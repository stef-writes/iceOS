import importlib

import pytest

pytestmark = [pytest.mark.smoke]


def test_import_runtime() -> None:
    """Ensure ice_api.main imports without errors."""
    importlib.import_module("ice_api.main") 