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

import sys

# ---------------------------------------------------------------------------
# Canonical model modules live locally in this package
# ---------------------------------------------------------------------------
from . import node_models as _node_models  # noqa: F401 (re-export)

# Re-export their public symbols at package top-level so that
# ``from ice_sdk.models import NodeConfig`` keeps working.
globals().update(_node_models.__dict__)

# ---------------------------------------------------------------------------
# Compatibility shims – register the old module paths that some external
# code may still attempt to import.  Mapping them in ``sys.modules`` avoids
# the need for deprecated code to change immediately while preserving the
# package boundary (we *do not* import from app.models here).
# ---------------------------------------------------------------------------

sys.modules.setdefault("ice_sdk.models.node_models", _node_models)
