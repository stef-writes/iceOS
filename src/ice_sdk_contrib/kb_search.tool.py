from __future__ import annotations

from pathlib import Path
from typing import Any, List

from ice_sdk.tools.base import BaseTool

__all__ = ["KBSearchTool"]

class KBSearchTool(BaseTool):
    """Search the mock knowledge base for lines containing the *query* string.

    This implementation is deliberately **simple** so it works without any
    external dependencies – perfect for unit tests and getting-started demos.
    Replace the body with a vector similarity search when you wire up a real
    DB.
    """

    name: str = "kb_search"
    description: str = (
        "Search the local knowledge base and return matching text snippets"
    )

    parameters_schema = {
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

    async def run(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        query: str = kwargs["query"]
        limit: int = kwargs.get("limit", 5)

        index_path = Path("knowledge_base") / ".mock_index.txt"
        if not index_path.exists():
            return {"results": []}

        results: List[str] = []
        with index_path.open(encoding="utf-8") as handle:
            for line in handle:
                if query.lower() in line.lower():
                    results.append(line.strip())
                    if len(results) >= limit:
                        break

        return {"results": results} 