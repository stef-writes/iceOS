from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import Field

from ice_core.base_tool import ToolBase


class MemorySearchTool(ToolBase):
    name: str = "memory_search_tool"
    description: str = Field(
        "Semantic search over pgvector (cosine), scoped by org and optional scope."
    )

    async def _execute_impl(
        self,
        *,
        query: str,
        scope: Optional[str] = None,
        limit: int = 10,
        org_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        from ice_api.services.semantic_memory_repository import search_semantic
        from ice_core.memory.embedders import get_embedder_from_env

        embedder = get_embedder_from_env()
        qvec = await embedder.embed(query)
        rows = await search_semantic(
            scope=scope, query_vec=qvec, limit=limit, org_id=org_id
        )
        out: Dict[str, Any] = {"results": rows}
        # Optional observability for debugging retrieval
        import os

        if os.getenv("ICE_DEBUG_RETRIEVAL", "0") == "1":
            out["debug"] = [
                {
                    "key": r.get("key"),
                    "cosine_similarity": r.get("cosine_similarity"),
                }
                for r in rows
            ]
        return out


def create_memory_search_tool(**kwargs: Any) -> MemorySearchTool:
    return MemorySearchTool(**kwargs)
