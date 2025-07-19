from .http_request_skill import HttpRequestSkill  # noqa: F401
from .search_skill import WebSearchConfig, WebSearchSkill  # noqa: F401
from .webhook_skill import WebhookSkill  # noqa: F401

try:
    from ..registry import global_skill_registry

    global_skill_registry.register("http_request", HttpRequestSkill())
    global_skill_registry.register("webhook_emitter", WebhookSkill())
except Exception:  # pragma: no cover
    pass
