"""HTTP request tool for making GET/POST requests."""

from __future__ import annotations

import asyncio
import base64
from typing import Any, ClassVar, Dict, List, Optional

import httpx

from ..base import BaseTool, ToolError


class HttpRequestTool(BaseTool):
    """Perform a simple HTTP request (GET or POST).

    Intended for static content fetches; for dynamic APIs prefer specialised
    provider-aware tools.
    """

    name: ClassVar[str] = "http_request"
    description: ClassVar[str] = (
        "Make an HTTP GET/POST request and return the response body (truncated)."
    )
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST"],
                "default": "GET",
            },
            "url": {"type": "string", "description": "Request URL"},
            "params": {
                "type": "object",
                "description": "Query parameters",
                "default": {},
            },
            "data": {"type": "object", "description": "POST body data", "default": {}},
            "timeout": {"type": "number", "default": 10.0},
            "attempts": {
                "type": "integer",
                "default": 5,
                "minimum": 1,
                "maximum": 10,
                "description": "Number of retry attempts on network failure",
            },
            "max_bytes": {
                "type": "integer",
                "default": 65536,
                "description": "Maximum bytes to return",
            },
            "base64": {
                "type": "boolean",
                "default": False,
                "description": "Return body as base64",
            },
        },
        "required": ["url"],
    }
    # Capability taxonomy -------------------------------------------------
    tags: ClassVar[List[str]] = ["web", "http", "io"]

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "status_code": {"type": "integer"},
            "headers": {"type": "object"},
            "body": {"type": "string"},
            "truncated": {"type": "boolean"},
        },
        "required": ["status_code", "body"],
    }

    async def run(self: "HttpRequestTool", **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        method: str = kwargs.get("method", "GET").upper()
        if method not in {"GET", "POST"}:
            raise ToolError("method must be 'GET' or 'POST'")

        url: str = kwargs["url"]
        params: Dict[str, Any] = kwargs.get("params", {})
        data: Optional[Dict[str, Any]] = kwargs.get("data")
        timeout: float = kwargs.get("timeout", 10.0)
        attempts: int = kwargs.get("attempts", 5)
        if attempts < 1 or attempts > 10:
            raise ToolError("'attempts' must be between 1 and 10")

        max_bytes: int = kwargs.get("max_bytes", 65536)
        wants_b64: bool = kwargs.get("base64", False)

        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if method == "GET":
                        resp = await client.get(url, params=params)
                    else:
                        resp = await client.post(url, params=params, json=data)
                break  # Success, exit retry loop
            except Exception as exc:  # pragma: no cover – network errors
                if attempt == attempts:
                    # Exhausted retries; raise detailed error
                    raise ToolError(
                        f"HTTP request failed after {attempts} attempts: {exc}"
                    ) from exc
                # Simple exponential backoff (0.1, 0.2, 0.4, ...)
                await asyncio.sleep(0.1 * 2 ** (attempt - 1))

        content: bytes = resp.content[:max_bytes]
        body: str | None
        if wants_b64:
            body = base64.b64encode(content).decode()
        else:
            try:
                body = content.decode()
            except UnicodeDecodeError:
                body = base64.b64encode(content).decode()

        return {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": body,
            "truncated": len(resp.content) > max_bytes,
        }
