"""Analytics tools for marketplace performance tracking."""

from .analytics_tracker_tool import AnalyticsTrackerTool
from ice_core.models import NodeType

# Register with unified registry
try:
    from ice_core.unified_registry import registry
    registry.register_instance(NodeType.TOOL, "analytics_tracker", AnalyticsTrackerTool())
except Exception:  # pragma: no cover
    pass

__all__ = ["AnalyticsTrackerTool"] 