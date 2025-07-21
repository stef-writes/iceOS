from .http_request_skill import HttpRequestSkill
from .search_skill import WebSearchSkill
from .webhook_skill import WebhookSkill

try:
    from ..registry import global_skill_registry

    global_skill_registry.register("http_request", HttpRequestSkill())
    global_skill_registry.register("webhook_emitter", WebhookSkill())
    global_skill_registry.register("web_search", WebSearchSkill())
except Exception:  # pragma: no cover
    pass
