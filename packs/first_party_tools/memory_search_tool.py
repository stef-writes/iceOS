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
        from ice_core.memory.embedders import HashEmbedder

        results: List[Dict[str, Any]] = []
        async for session in get_session():
            # Compute embedding (hash fallback). For OpenAI, swap to OpenAIEmbedder.
            embedder = HashEmbedder(dim=1536)
            qvec = await embedder.embed(query)

            rows = await session.execute(
                text(
                    """
                    SELECT id, scope, key, content_hash, model_version, meta_json, created_at
                         , 1 - (embedding <=> :qvec::vector) AS cosine_similarity
                    FROM semantic_memory
                    WHERE (:scope IS NULL OR scope = :scope) AND embedding IS NOT NULL
                    ORDER BY embedding <-> :qvec::vector
                    LIMIT :limit
                    """
                ),
                {"scope": scope, "qvec": qvec, "limit": limit},
            )
            for r in rows.mappings():
                row = dict(r)
                results.append(row)
        return {"results": results}


def create_memory_search_tool(**kwargs: Any) -> MemorySearchTool:
    return MemorySearchTool(**kwargs)
