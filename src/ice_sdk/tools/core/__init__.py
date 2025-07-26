"""Core data manipulation tools."""
from ice_sdk.tools.core.csv_tool import CSVTool
from ice_sdk.tools.core.base import DataTool

__all__ = ["CSVTool", "DataTool"]

# Auto-register core tools
from ice_sdk.unified_registry import registry
from ice_core.models.enums import NodeType

try:
    registry.register_instance(NodeType.TOOL, "csv", CSVTool())
except Exception:
    pass 