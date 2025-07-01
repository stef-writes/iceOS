from __future__ import annotations

"""ice_sdk_contrib – official *extra* helpers for iceOS.

This sub-package bundles reusable, **optional** components that do **not** belong
in the lean `ice_sdk` core but are still useful across many projects.

Public API:
    • `kb_router` – FastAPI router that provides upload/ingest endpoints for a
      mock knowledge-base used in demos & tests.
    • `KBSearchTool` – lightweight tool that queries the mock index.

Importing this package has *no* side-effects – the router & tool are merely
made importable.  Tool registration happens via the orchestrator's normal
file-system discovery of `*.tool.py` modules.
"""

from importlib import import_module as _import_module
from types import ModuleType as _ModuleType
from typing import TYPE_CHECKING as _TYPE_CHECKING

# ruff: noqa: E402

# Lazily import heavy dependencies (FastAPI) only when required -------------

# Routers -------------------------------------------------------------------

try:
    from .kb_router import router as kb_router  # noqa: F401
except Exception:  # pragma: no cover – optional dependency missing
    # Users who did not install FastAPI will simply not have the router.
    kb_router = None  # type: ignore

# Tools ---------------------------------------------------------------------

# The `KBSearchTool` lives in a `*.tool.py` file so auto-discovery will find
# it at runtime even if we do not import here.  For completeness we still
# expose the class when FastAPI is available so static analysers see it.
if not _TYPE_CHECKING:
    try:
        _kb_mod: _ModuleType = _import_module("ice_sdk_contrib.kb_search.tool")
        KBSearchTool = getattr(_kb_mod, "KBSearchTool")  # type: ignore
        del _kb_mod
    except Exception:
        KBSearchTool = None  # type: ignore

__all__ = [
    "kb_router",
    "KBSearchTool",
]
