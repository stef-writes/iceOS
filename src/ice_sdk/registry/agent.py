"""Agent registry for backward compatibility.

This module provides the global_agent_registry that was previously defined here.
All functionality has been moved to the unified registry.
"""

from ice_sdk.unified_registry import global_agent_registry

__all__ = ["global_agent_registry"] 