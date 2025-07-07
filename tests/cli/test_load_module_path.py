from __future__ import annotations

import sys
from pathlib import Path

from ice_sdk.plugin_discovery import load_module_from_path


def test_load_module_from_path(tmp_path: Path):
    """load_module_from_path should load the module and expose attributes."""
    sample = tmp_path / "sample.py"
    sample.write_text("""\nx = 42\ndef foo():\n    return 'bar'\n""")

    module = load_module_from_path(sample)

    # Sanity checks ----------------------------------------------------------
    assert hasattr(module, "x")
    assert module.x == 42
    assert hasattr(module, "foo")
    assert module.foo() == "bar"
    assert module.__name__ in sys.modules  # reloading works
