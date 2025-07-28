from .http_request_tool import HttpRequestTool
from ice_core.models import NodeType
from .search_tool import WebSearchTool
from .arxiv_search_tool import ArxivSearchTool
from .webhook_tool import WebhookEmitterTool

try:
    from ice_core.unified_registry import registry

    registry.register_instance(NodeType.TOOL, "http_request", HttpRequestTool())
    registry.register_instance(NodeType.TOOL, "webhook_emitter", WebhookEmitterTool())
    registry.register_instance(NodeType.TOOL, "web_search", WebSearchTool())
    registry.register_instance(NodeType.TOOL, "arxiv_search", ArxivSearchTool())
except Exception:  # pragma: no cover
    pass
