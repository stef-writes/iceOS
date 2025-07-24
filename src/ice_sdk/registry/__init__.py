"""Registry package for backward compatibility.

This package provides backward compatible imports for the old registry system.
All functionality has been moved to the unified registry.
"""

from ice_sdk.unified_registry import (
    global_agent_registry,
    global_chain_registry,
    registry,
)

__all__ = [
    "global_agent_registry", 
    "global_chain_registry",
    "registry",
] 