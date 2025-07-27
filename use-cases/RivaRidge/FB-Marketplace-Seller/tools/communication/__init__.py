"""Communication tools for customer interaction."""

from .message_parser_tool import MessageParserTool
from ice_core.models import NodeType

# Register with unified registry
try:
    from ice_core.unified_registry import registry
    registry.register_instance(NodeType.TOOL, "message_parser", MessageParserTool())
except Exception:  # pragma: no cover
    pass

__all__ = ["MessageParserTool"] 