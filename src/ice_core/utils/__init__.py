"""Utility helpers that have **zero** runtime dependencies beyond the standard library.

Anything imported here is considered safe for lower layers (sdk/orchestrator)
without introducing cycles.
"""

from __future__ import annotations

__all__: list[str] = [
    "deprecation",
]

from . import deprecation  # noqa: E402, F401 import after __all__
