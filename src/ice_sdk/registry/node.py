"""Node registry for backward compatibility.

This module provides executor registry functions that were previously defined here.
All functionality has been moved to the unified registry.
"""

from ice_sdk.unified_registry import get_executor, register_node

__all__ = ["get_executor", "register_node"] 