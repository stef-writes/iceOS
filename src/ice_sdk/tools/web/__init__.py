"""Web and network tools for HTTP requests, search, and webhooks."""

from __future__ import annotations

from .http_tool import HttpRequestTool
from .search_tool import WebSearchTool

# Original emitter tool -------------------------------------------------
from .webhook_tool import WebhookEmitterTool

# Backwards-compatible alias -------------------------------------------
WebhookTool = WebhookEmitterTool  # noqa: N816

__all__ = [
    "HttpRequestTool",
    "WebSearchTool",
    "WebhookEmitterTool",
    "WebhookTool",
]
