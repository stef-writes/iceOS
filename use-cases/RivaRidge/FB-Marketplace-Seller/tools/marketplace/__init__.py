"""Marketplace-specific tools."""

from .facebook_api_tool import FacebookAPITool
from .price_research_tool import PriceResearchTool

# Register tools with the unified registry
from ice_core.unified_registry import registry
from ice_core.models import NodeType

try:
    registry.register_instance(NodeType.TOOL, "facebook_api", FacebookAPITool())
    registry.register_instance(NodeType.TOOL, "price_research", PriceResearchTool())
except Exception:
    pass

__all__ = [
    "FacebookAPITool",
    "PriceResearchTool"
] 