from __future__ import annotations

from pathlib import Path
from typing import Any, AsyncIterator, ClassVar, Dict, List

from ..base import BaseTool, ToolError

__all__ = ["KBSearchTool"]


class KBSearchTool(BaseTool):
    """Search the mock knowledge-base for lines containing the *query* string.

    This implementation is deliberately *simple* so it works without external
    dependencies – perfect for unit tests and getting-started demos. Replace
    the body with a vector similarity search when you wire up a real DB.
    """

    name: ClassVar[str] = "kb_search"
    description: ClassVar[str] = (
        "Search the local knowledge base and return matching text snippets"
    )

    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
                "default": 5,
                "description": "Maximum number of snippets to return",
            },
        },
        "required": ["query"],
    }

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Matching text snippets from the knowledge base",
            }
        },
        "required": ["results"],
    }

    tags: ClassVar[List[str]] = ["search", "kb"]

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        query: str = kwargs["query"]
        limit: int = kwargs.get("limit", 5)
        if limit < 1 or limit > 50:
            raise ToolError("'limit' must be between 1 and 50")

        index_path = Path("knowledge_base") / ".mock_index.txt"
        if not index_path.exists():
            return {"results": []}

        results: List[str] = []
        async for line in _aiter_lines(index_path):
            if query.lower() in line.lower():
                results.append(line.strip())
                if len(results) >= limit:
                    break

        return {"results": results}


async def _aiter_lines(path: Path) -> AsyncIterator[str]:
    """Asynchronously yield lines from *path* (non-blocking)."""
    import asyncio

    loop = asyncio.get_event_loop()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            # Offload string conversion to thread to avoid blocking if large
            yield await loop.run_in_executor(None, str, line)
