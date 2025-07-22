from __future__ import annotations

"""Canonical package for deterministic **tool** implementations.

This package supersedes the legacy ``ice_sdk.skills`` namespace.  For the
moment we keep a *thin re-export shim* so that importing either path works,
allowing gradual migration while downstream projects update their imports.

After the v1.2 release the old package will be removed entirely.
"""

import importlib
import sys
import types
import warnings
from types import ModuleType

# ---------------------------------------------------------------------------
# Self-alias so ``import ice_sdk.skills`` resolves to this package -----------
# ---------------------------------------------------------------------------

sys.modules.setdefault("ice_sdk.skills", sys.modules[__name__])

# Expose submodules under both namespaces -----------------------------------

for _sub in ("system", "db", "web", "service", "registry", "base"):
    try:
        _mod = importlib.import_module(f"{__name__}.{_sub}")
        sys.modules[f"ice_sdk.skills.{_sub}"] = _mod  # legacy alias
    except ModuleNotFoundError:  # pragma: no cover – safety guard
        continue

# Expose key symbols at package root for convenient imports --------------

try:
    from .base import SkillBase, ToolContext, function_tool

    globals()["SkillBase"] = SkillBase  # type: ignore
    globals()["ToolContext"] = ToolContext  # type: ignore
    globals()["function_tool"] = function_tool  # type: ignore
    __all__.extend(["SkillBase", "ToolContext", "function_tool"])
except Exception:  # pragma: no cover – safety
    pass

# ---------------------------------------------------------------------------
# Deprecation warning for old import path -----------------------------------
# ---------------------------------------------------------------------------

warnings.warn(
    "'ice_sdk.skills' package is deprecated; use 'ice_sdk.tools' instead.",
    DeprecationWarning,
    stacklevel=2,
)
 
# Public API surface --------------------------------------------------------

# Dynamically gather from submodules that define __all__ --------------------

__all__: list[str] = []

for _sub in ("base", "service", "registry", "system", "db", "web"):
    try:
        _mod = importlib.import_module(f"{__name__}.{_sub}")
        __all__.extend(getattr(_mod, "__all__", []))
    except ModuleNotFoundError:
        continue 

# ---------------------------------------------------------------------------
# Auto-import core subpackages so their registration side-effects run -------
# ---------------------------------------------------------------------------

for _auto in ("system", "db", "web"):
    try:
        importlib.import_module(f"{__name__}.{_auto}")
    except ModuleNotFoundError:  # pragma: no cover – optional package
        pass 