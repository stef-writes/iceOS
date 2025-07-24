"""Chain registry for backward compatibility.

This module provides the global_chain_registry that was previously defined here.
All functionality has been moved to the unified registry.
"""

from ice_sdk.unified_registry import global_chain_registry

__all__ = ["global_chain_registry"] 