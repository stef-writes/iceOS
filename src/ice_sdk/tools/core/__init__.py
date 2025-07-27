"""Core data manipulation tools."""
from ice_sdk.tools.core.csv_tool import CSVTool

__all__ = ["CSVTool"]

# Auto-register core tools
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType

try:
    registry.register_instance(NodeType.TOOL, "csv", CSVTool())
except Exception:
    pass 