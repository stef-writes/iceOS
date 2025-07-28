"""Simple workflows for Facebook Marketplace automation using clean iceOS patterns."""

from .marketplace_automation import (
    create_marketplace_automation_workflow,
    create_simple_listing_workflow
)
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType

# Auto-register so blueprints can reference workflow_ref directly
try:
    registry.register_instance(
        NodeType.WORKFLOW,
        "marketplace_automation",
        create_marketplace_automation_workflow(),
    )
    registry.register_instance(
        NodeType.WORKFLOW,
        "simple_listing",
        create_simple_listing_workflow(),
    )
except Exception:
    # Ignore double-registration when reloaded
    pass

__all__ = [
    "create_marketplace_automation_workflow", 
    "create_simple_listing_workflow"
] 