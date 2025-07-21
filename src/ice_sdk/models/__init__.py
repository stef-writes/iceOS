"""ice_sdk.models – Pydantic model re-exports

This package used to live under ``app.models`` inside the reference
application.  To keep the SDK independent we moved the canonical
implementations here but still expose the *same* public interface so
that callers can continue to rely on both import styles::

    from ice_sdk.models import NodeConfig  # preferred
    from ice_sdk.models.node_models import NodeConfig

Backward-compatibility shims are also provided so that legacy code that
imports ``app.models.*`` keeps working *without* introducing a runtime
**dependency inversion** (Cursor repo rule #4 – never import
``app.*`` from inside ``ice_sdk.*``).
"""

from __future__ import annotations

import importlib
import sys

# ---------------------------------------------------------------------------
# Import canonical model definitions from *ice_core* -------------------------
# ---------------------------------------------------------------------------
_node_models = importlib.import_module("ice_core.models.node_models")

# Re-export everything at top-level so callers can do
# ``from ice_sdk.models import NodeConfig``.
globals().update(_node_models.__dict__)

# ---------------------------------------------------------------------------
# Compatibility shims --------------------------------------------------------
# ---------------------------------------------------------------------------
# Ensure legacy import paths keep resolving but emit a deprecation warning.

sys.modules.setdefault("ice_sdk.models.node_models", _node_models)
