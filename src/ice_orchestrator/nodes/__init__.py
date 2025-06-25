"""Legacy import-path compatibility for `ice_orchestrator.nodes.*`.

This sub-package re-exports the canonical implementations that now live under
`ice_sdk`.  It allows third-party code that still does::

    from ice_orchestrator.nodes.base import BaseNode

or::

    from ice_orchestrator.nodes import BaseNode

to keep working without modifications.

The module adds *zero* runtime side-effects other than importing the upstream
symbol and registering an alias in ``sys.modules``.  New code should import
``BaseNode`` directly from ``ice_sdk.base_node`` instead.
"""

from importlib import import_module as _import_module
import sys as _sys
from types import ModuleType as _ModuleType
import os as _os

# Check feature flag ---------------------------------------------------------
if _os.getenv("ICE_SDK_ENABLE_LEGACY_IMPORTS", "0") not in {"1", "true", "True"}:
    # Compatibility layers disabled – make import fail as if module missing.
    raise ImportError(
        "Legacy import paths for 'ice_orchestrator.nodes.*' are disabled. "
        "Set ICE_SDK_ENABLE_LEGACY_IMPORTS=1 to re-enable."
    )

# ---------------------------------------------------------------------------
# Re-export symbols from their canonical location ---------------------------
# ---------------------------------------------------------------------------

BaseNode = _import_module("ice_sdk.base_node").BaseNode  # type: ignore[attr-defined]

__all__ = [
    "BaseNode",
]

# ---------------------------------------------------------------------------
# Populate the legacy sub-module ``ice_orchestrator.nodes.base`` so that
# "from ice_orchestrator.nodes.base import BaseNode" keeps working.
# ---------------------------------------------------------------------------

_base_mod_name = __name__ + ".base"
_base_mod = _ModuleType(_base_mod_name)
_base_mod.BaseNode = BaseNode  # type: ignore[attr-defined]

_sys.modules[_base_mod_name] = _base_mod 