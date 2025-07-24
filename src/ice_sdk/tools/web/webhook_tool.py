from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional

import httpx
from pydantic import AnyHttpUrl, BaseModel, Field

from ...utils.errors import ToolExecutionError
from ..base import ToolBase

__all__ = ["WebhookEmitterTool"]

class _WebhookArgs(BaseModel):
    url: AnyHttpUrl
    headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    timeout: float = 5.0

class WebhookEmitterTool(ToolBase):
    """POST JSON payloads to an external webhook."""

    name: str = "webhook_emitter"
    description: str = "Send event payloads to a webhook endpoint via HTTP POST."
    # Annotate as class variable
    tags: ClassVar[list[str]] = ["integration", "webhook", "event"]

    def get_required_config(self) -> list[str]:
        return []

    async def _execute_impl(
        self,
        *,
        ctx: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not hasattr(ctx, "metadata"):
            raise ToolExecutionError("'ctx' with metadata is required")

        args = _WebhookArgs(**kwargs)
        async with httpx.AsyncClient(timeout=args.timeout) as client:
            resp = await client.post(
                str(args.url), json=ctx.metadata, headers=args.headers
            )
            resp.raise_for_status()
        return {"status_code": resp.status_code}
