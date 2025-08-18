from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field

from ice_core.base_tool import ToolBase


class MemorySearchTool(ToolBase):
    name: str = "memory_search_tool"
    description: str = Field(
        "Search semantic memory entries by exact key or scope prefix (placeholder vector search)"
    )

    async def _execute_impl(
        self,
        *,
        query: str,
        scope: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        from sqlalchemy import text

        from ice_api.db.database_session_async import get_session

        results: List[Dict[str, Any]] = []
        async for session in get_session():
            rows = await session.execute(
                text(
                    """
                    SELECT id, scope, key, content_hash, model_version, meta_json, created_at
                    FROM semantic_memory
                    WHERE (:scope IS NULL OR scope = :scope) AND (key ILIKE :q)
                    ORDER BY id DESC
                    LIMIT :limit
                    """
                ),
                {"scope": scope, "q": f"%{query}%", "limit": limit},
            )
            for r in rows.mappings():
                results.append(dict(r))
        return {"results": results}


def create_memory_search_tool(**kwargs: Any) -> MemorySearchTool:
    return MemorySearchTool(**kwargs)
