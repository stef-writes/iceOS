"""AI-powered tools using LLM services."""
from ice_sdk.tools.ai.base import AITool
from ice_sdk.tools.ai.insights_tool import InsightsTool
from ice_sdk.tools.ai.summarizer_tool import SummarizerTool
from ice_sdk.tools.ai.line_item_generator_tool import LineItemGeneratorTool

__all__ = ["AITool", "InsightsTool", "SummarizerTool", "LineItemGeneratorTool"]

# Register AI tools
from ice_sdk.unified_registry import registry
from ice_core.models.enums import NodeType

try:
    registry.register_instance(NodeType.TOOL, "insights", InsightsTool())
    registry.register_instance(NodeType.TOOL, "summarizer", SummarizerTool())
    registry.register_instance(NodeType.TOOL, "line_item_generator", LineItemGeneratorTool())
except Exception:
    pass 