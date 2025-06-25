"""Deterministic utility tools that have no external side-effects
(other than optional network I/O for *HttpRequestTool*).

These are lightweight examples used in documentation, tests and examples.
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any, ClassVar, Dict, List, Optional

import httpx

from ..base import BaseTool, ToolError

__all__ = [
    "SleepTool",
    "HttpRequestTool",
    "SumTool",
]


class SleepTool(BaseTool):
    """Pause execution for *n* seconds.

    Useful for demo workflows that need to simulate latency or rate-limit.
    """

    name: ClassVar[str] = "sleep"
    description: ClassVar[str] = "Pause execution for a number of seconds"
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "seconds": {
                "type": "number",
                "minimum": 0,
                "maximum": 60,
                "description": "Duration of the sleep in seconds (max 60)",
            }
        },
        "required": ["seconds"],
    }

    async def run(self, **kwargs) -> Dict[str, Any]:  # type: ignore[override]
        seconds: float = kwargs.get("seconds", 0)
        if seconds < 0 or seconds > 60:
            raise ToolError("'seconds' must be between 0 and 60")
        await asyncio.sleep(seconds)
        return {"slept": seconds}


class HttpRequestTool(BaseTool):
    """Perform a simple HTTP request (GET or POST).

    Intended for static content fetches; for dynamic APIs prefer specialised
    provider-aware tools.
    """

    name: ClassVar[str] = "http_request"
    description: ClassVar[str] = "Make an HTTP GET/POST request and return the response body (truncated)."
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST"],
                "default": "GET",
            },
            "url": {"type": "string", "description": "Request URL"},
            "params": {"type": "object", "description": "Query parameters", "default": {}},
            "data": {"type": "object", "description": "POST body data", "default": {}},
            "timeout": {"type": "number", "default": 10.0},
            "attempts": {
                "type": "integer",
                "default": 5,
                "minimum": 1,
                "maximum": 10,
                "description": "Number of retry attempts on network failure",
            },
            "max_bytes": {"type": "integer", "default": 65536, "description": "Maximum bytes to return"},
            "base64": {"type": "boolean", "default": False, "description": "Return body as base64"},
        },
        "required": ["url"],
    }

    async def run(self, **kwargs) -> Dict[str, Any]:  # type: ignore[override]
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

        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if method == "GET":
                        resp = await client.get(url, params=params)
                    else:
                        resp = await client.post(url, params=params, json=data)
                break  # Success, exit retry loop
            except Exception as exc:  # pragma: no cover – network errors
                last_exc = exc
                if attempt == attempts:
                    # Exhausted retries; raise detailed error
                    raise ToolError(f"HTTP request failed after {attempts} attempts: {exc}") from exc
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


class SumTool(BaseTool):
    """Return the arithmetic sum of a list of numbers."""

    name: ClassVar[str] = "sum"
    description: ClassVar[str] = "Add a list of numbers and return the total"
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "numbers": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Numbers to add",
            }
        },
        "required": ["numbers"],
    }

    async def run(self, **kwargs) -> Dict[str, Any]:  # type: ignore[override]
        numbers: List[float] = kwargs.get("numbers", [])
        if not isinstance(numbers, list):
            raise ToolError("'numbers' must be an array of numbers")
        try:
            total = sum(float(x) for x in numbers)
        except Exception as exc:
            raise ToolError(f"Invalid number in input: {exc}") from exc
        return {"sum": total} 