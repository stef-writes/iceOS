"""Internal MCP tool – thin wrapper around the new /api/v1/mcp endpoints.

For now we perform a blocking HTTP call to *start_run* with an inline blueprint.
The tool is **core** because it targets the local iceOS control-plane, not a
third-party vendor.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, ClassVar, Dict, List

import httpx
from pydantic import BaseModel

from ..base import BaseTool, ToolError

__all__ = ["InternalMCPTool"]


class _NodeSpec(BaseModel):
    id: str
    type: str

    model_config = {"extra": "allow"}


class _Blueprint(BaseModel):
    nodes: List[_NodeSpec]
    blueprint_id: str | None = None
    version: str = "1.0.0"


class InternalMCPTool(BaseTool):
    """Submit a *Blueprint* to /api/v1/mcp and await the final result."""

    name: ClassVar[str] = "internal_mcp"
    description: ClassVar[str] = "Execute a blueprint via the internal MCP endpoint"

    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "blueprint": {"type": "object"},
            "max_parallel": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["blueprint"],
    }

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "output": {"type": "object"},
            "error": {"type": "string", "nullable": True},
        },
        "required": ["success", "output"],
    }

    # ------------------------------------------------------------------
    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        blueprint: Dict[str, Any] = kwargs.get("blueprint", {})
        max_parallel: int = int(kwargs.get("max_parallel", 5))
        base_url = os.getenv("ICEOS_API", "http://localhost:8000")  # noqa: D401
        mcp_url = f"{base_url.rstrip('/')}/api/v1/mcp/runs"

        payload = {
            "blueprint": blueprint,
            "options": {"max_parallel": max_parallel},
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                ack_resp = await client.post(mcp_url, json=payload)
                ack_resp.raise_for_status()
                ack = ack_resp.json()
                status_url = f"{base_url}{ack['status_endpoint']}"

                # Poll until finished (could upgrade to SSE later)
                while True:
                    res_resp = await client.get(status_url)
                    if res_resp.status_code == 202:
                        await asyncio.sleep(0.5)
                        continue
                    res_resp.raise_for_status()
                    result = res_resp.json()
                    return {
                        "success": bool(result["success"]),
                        "output": result.get("output", {}),
                        "error": result.get("error"),
                    }
        except Exception as exc:  # pragma: no cover
            raise ToolError(f"InternalMCPTool failed: {exc}") from exc
