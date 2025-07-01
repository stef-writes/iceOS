"""WebhookEmitterTool – send event payloads to an HTTP endpoint.

The tool is purposefully thin: it **only** performs network IO, satisfying the
repo rule that external side-effects live inside Tool implementations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from pydantic import AnyHttpUrl, BaseModel, Field

from .base import BaseTool, ToolContext

__all__ = ["WebhookEmitterTool"]


class _WebhookArgs(BaseModel):
    """Arguments accepted by :class:`WebhookEmitterTool`."""

    url: AnyHttpUrl
    headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    timeout: float = 5.0


class WebhookEmitterTool(BaseTool):
    """POST JSON payloads to an external webhook."""

    name = "webhook_emitter"
    description = "Send event payloads to a webhook endpoint via HTTP POST."

    async def run(self, ctx: ToolContext, **kwargs: Any) -> Any:  # noqa: D401, WPS110 – ctx required by contract
        args = _WebhookArgs(**kwargs)

        async with httpx.AsyncClient(timeout=args.timeout) as client:
            resp = await client.post(str(args.url), json=ctx.metadata, headers=args.headers)
            resp.raise_for_status()

        return {"status_code": resp.status_code} 