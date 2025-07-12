"""Tests for :pyfunc:`@public` decorator ensuring symbol export behaviour."""

from __future__ import annotations

import sys
import types

from ice_sdk.utils.public import public  # noqa: F401


def _make_temp_module(name: str = "tmp_public_module"):  # pragma: no cover – helper
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


def test_public_decorator_adds_symbol_to___all__():
    module = _make_temp_module()

    code = """
from ice_sdk.utils.public import public

@public
class Foo:
    ...

@public
def bar() -> str:
    return "bar"
    """
    exec(code, module.__dict__)

    assert "Foo" in module.__all__
    assert "bar" in module.__all__


def test_public_decorator_respects_custom_export_name():
    module = _make_temp_module("tmp_public_module_alias")

    code = """
from ice_sdk.utils.public import public

@public(name="qux_alias")
class Qux:
    ...
    """
    exec(code, module.__dict__)

    assert "qux_alias" in module.__all__


def test_public_decorator_idempotent():
    module = _make_temp_module("tmp_public_module_idempotent")

    code = """
from ice_sdk.utils.public import public

@public
@public  # applied twice
class Zap:
    ...
    """
    exec(code, module.__dict__)

    # Duplicates should not occur within __all__
    assert module.__all__.count("Zap") == 1
