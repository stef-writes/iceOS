from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import Field

from ice_core.base_tool import ToolBase


class MemoryWriteTool(ToolBase):
    name: str = "memory_write_tool"
    description: str = Field(
        "Store a semantic memory entry with optional scope and metadata"
    )

    async def _execute_impl(
        self,
        *,
        key: str,
        content: str,
        scope: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from sqlalchemy import text

        from ice_api.db.database_session_async import get_session
        from ice_core.memory.embedders import HashEmbedder

        async for session in get_session():
            # Compute embedding (hash fallback; can be swapped to OpenAIEmbedder)
            embedder = HashEmbedder(dim=1536)
            embedding_vec = await embedder.embed(content)
            embedding = "[" + ",".join(f"{x:.6f}" for x in embedding_vec) + "]"

            await session.execute(
                text(
                    """
                    INSERT INTO semantic_memory (scope, key, content_hash, model_version, meta_json, embedding)
                    VALUES (:scope, :key, :content_hash, :model_version, :meta_json, :embedding::vector)
                    ON CONFLICT (content_hash) DO NOTHING
                    """
                ),
                {
                    "scope": scope or "default",
                    "key": key,
                    "content_hash": self._hash_content(content),
                    "model_version": None,
                    "meta_json": metadata or {"content": content},
                    "embedding": embedding,
                },
            )
            await session.commit()
        return {"ok": True, "key": key, "scope": scope or "default"}

    @staticmethod
    def _hash_content(content: str) -> str:
        import hashlib

        return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_memory_write_tool(**kwargs: Any) -> MemoryWriteTool:
    return MemoryWriteTool(**kwargs)
