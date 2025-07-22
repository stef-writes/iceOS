from .http_request_skill import HttpRequestSkill
from .search_skill import WebSearchSkill
from .webhook_skill import WebhookSkill

try:
    from ice_sdk.registry.tool import global_tool_registry

    global_tool_registry.register("http_request", HttpRequestSkill())
    global_tool_registry.register("webhook_emitter", WebhookSkill())
    global_tool_registry.register("web_search", WebSearchSkill())
except Exception:  # pragma: no cover
    pass
