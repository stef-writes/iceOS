from __future__ import annotations

"""ice_builder – Unified workflow building package.

During the v0.1 hardening phase the natural-language (NL) generator is
*disabled by default* to avoid strict-typing violations bleeding into other
layers.  A feature flag allows developers to enable it locally while we
complete the refactor.
"""

import os
from contextlib import suppress
from importlib import metadata as _metadata
from typing import List as _List

# ---------------------------------------------------------------------------
# Public DSL surface (always available) -------------------------------------
# ---------------------------------------------------------------------------
from . import dsl as _dsl  # noqa: E402 – re-export order intentional
from .dsl import *  # noqa: F401,F403 – DSL builders

# ---------------------------------------------------------------------------
# Conditional NL generator export ------------------------------------------
# ---------------------------------------------------------------------------

ENABLE_NL_GENERATOR = os.getenv("ENABLE_NL_GENERATOR", "0") == "1"

with suppress(ImportError):
    if ENABLE_NL_GENERATOR:
        from .nl import append_tool_node, create_partial_blueprint  # noqa: F401

        __all_extra: _List[str] = [
            "append_tool_node",
            "create_partial_blueprint",
        ]
    else:  # Hardened builds: raise a warning to callers
        import warnings

        warnings.warn(
            "NL generator is temporarily disabled during protocol-compliance "
            "hardening.  Set ENABLE_NL_GENERATOR=1 to opt-in.",
            RuntimeWarning,
            stacklevel=2,
        )
        __all_extra = []

# ---------------------------------------------------------------------------
# Package metadata ----------------------------------------------------------
# ---------------------------------------------------------------------------

_public_all: _List[str] = globals().get("__all__", [])  # type: ignore[arg-type]
__all__: _List[str] = _public_all + _dsl.__all__ + __all_extra
# Resolve package version if distribution metadata is available; fall back to a
# neutral default to avoid import-time failures in non-installed environments
# (e.g., dockerized test image running from source).
try:  # pragma: no cover - trivial guard
    __version__ = _metadata.version("iceos")
except Exception:
    __version__ = "0.0.0"
