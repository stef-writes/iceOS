"""Context utilities moved to orchestrator.

All context management functionality has been moved to ice_orchestrator.context
for proper separation of concerns. The SDK should not contain runtime context logic.

To access context services, use ServiceLocator:
    from ice_sdk.services import ServiceLocator
    context_manager = ServiceLocator.get("context_manager")
"""

# This module is now empty - all context management is in orchestrator
__all__ = []
