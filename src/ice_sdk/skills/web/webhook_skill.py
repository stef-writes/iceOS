from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from pydantic import AnyHttpUrl, BaseModel, Field

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__ = ["WebhookSkill"]


class _WebhookArgs(BaseModel):
    url: AnyHttpUrl
    headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    timeout: float = 5.0


class WebhookSkill(SkillBase):
    """POST JSON payloads to an external webhook."""

    name: str = "webhook_emitter"
    description: str = "Send event payloads to a webhook endpoint via HTTP POST."
    tags = ["integration", "webhook", "event"]

    def get_required_config(self):  # noqa: D401
        return []

    async def _execute_impl(
        self,
        *,
        ctx: Any | None = None,
        input_data: Dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        # Accept both legacy *input_data* dict and direct keyword args
        input_data = {**(input_data or {}), **kwargs}
        ctx = ctx or input_data.pop("ctx", None)
        if ctx is None or not hasattr(ctx, "metadata"):
            raise SkillExecutionError("'ctx' with metadata is required")

        args = _WebhookArgs(**input_data)
        async with httpx.AsyncClient(timeout=args.timeout) as client:
            resp = await client.post(
                str(args.url), json=ctx.metadata, headers=args.headers
            )
            resp.raise_for_status()
        return {"status_code": resp.status_code}
