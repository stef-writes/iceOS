"""Core utilities for ice_sdk (validation, retries, helpers).

This subpackage hosts small, side-effect-free helpers that can be re-used by
multiple layers (agents, tools, orchestrator) without creating dependency
cycles.  External IO is *strictly* forbidden here – follow Cursor rule #2.
"""

from .validation import validate_or_raise

__all__ = [
    "validate_or_raise",
]
