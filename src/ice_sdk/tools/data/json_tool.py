"""JSON query tool using JMESPath."""

from __future__ import annotations

import asyncio
import base64
import json
import re
from pathlib import Path
from typing import Any, ClassVar, Dict, List

import httpx

try:  # Optional dependency for JMESPath queries
    import jmespath  # type: ignore
except Exception:  # pragma: no cover – optional dep
    jmespath = None  # type: ignore

from ..base import BaseTool, ToolError

_HTTP_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


class JsonQueryTool(BaseTool):
    """Run a JMESPath query against JSON data from string, file or URL."""

    name: ClassVar[str] = "json_query"
    description: ClassVar[str] = "Query JSON using JMESPath expressions"

    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "JMESPath expression to evaluate",
            },
            "source": {
                "type": "string",
                "description": "JSON string, file path or URL",
            },
            "max_bytes": {
                "type": "integer",
                "default": 32768,
                "minimum": 256,
                "maximum": 262144,
                "description": "Maximum bytes of JSON result to return",
            },
            "base64": {
                "type": "boolean",
                "default": False,
                "description": "Encode result body as base64 string",
            },
        },
        "required": ["query", "source"],
    }

    tags: ClassVar[List[str]] = ["json", "query", "data"]

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "result": {},  # type: ignore[typeddict-item]
            "truncated": {"type": "boolean"},
        },
        "required": ["result", "truncated"],
    }

    async def _load_source(self, source: str) -> Any:  # noqa: ANN401 – dynamic JSON
        # Fast heuristic – if starts with '{' or '[' treat as inline JSON string.
        if source.strip().startswith(("{", "[")):
            return json.loads(source)
        if _HTTP_PATTERN.match(source):  # Remote fetch
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(source)
                res.raise_for_status()
                return res.json()
        # Else treat as local path ----------------------------
        try:
            text = await asyncio.to_thread(Path(source).read_text, encoding="utf-8")
            return json.loads(text)
        except FileNotFoundError as exc:
            raise ToolError(f"File not found: {source}") from exc

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        if jmespath is None:  # pragma: no cover – missing optional dep
            raise ToolError("'jmespath' package is required for JsonQueryTool")

        query_expr: str = kwargs.get("query")  # type: ignore[assignment]
        source: str = kwargs.get("source")  # type: ignore[assignment]
        if not query_expr:
            raise ToolError("'query' argument is required")
        if not source:
            raise ToolError("'source' argument is required")

        max_bytes: int = kwargs.get("max_bytes", 32768)
        wants_b64: bool = kwargs.get("base64", False)

        data = await self._load_source(source)

        try:
            compiled = jmespath.compile(query_expr)
            result = compiled.search(data)
        except Exception as exc:  # noqa: BLE001 – user query errors
            raise ToolError(f"JMESPath evaluation failed: {exc}") from exc

        # Serialise & size-check -------------------------------------------
        raw_bytes = json.dumps(result, ensure_ascii=False, default=str).encode()
        truncated = False
        if len(raw_bytes) > max_bytes:
            truncated = True
            raw_bytes = raw_bytes[:max_bytes]

        if wants_b64:
            body = base64.b64encode(raw_bytes).decode()
        else:
            body = raw_bytes.decode(errors="replace")

        return {"result": body, "truncated": truncated}
