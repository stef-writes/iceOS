"""Inventory management tools."""

from .inventory_analyzer_tool import InventoryAnalyzerTool
from .image_enhancer_tool import ImageEnhancerTool

# Register tools with the unified registry
from ice_core.unified_registry import registry
from ice_core.models import NodeType

try:
    registry.register_instance(NodeType.TOOL, "inventory_analyzer", InventoryAnalyzerTool())
    registry.register_instance(NodeType.TOOL, "image_enhancer", ImageEnhancerTool())
except Exception:
    pass

__all__ = [
    "InventoryAnalyzerTool",
    "ImageEnhancerTool"
] 