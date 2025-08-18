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
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        from ice_api.services.semantic_memory_repository import insert_semantic_entry
        from ice_core.memory.embedders import get_embedder_from_env

        embedder = get_embedder_from_env()
        embedding_vec = await embedder.embed(content)
        await insert_semantic_entry(
            scope=scope or "default",
            key=key,
            content_hash=self._hash_content(content),
            meta_json=metadata or {"content": content},
            embedding_vec=embedding_vec,
            org_id=org_id,
            user_id=user_id,
            model_version=None,
        )
        return {
            "ok": True,
            "key": key,
            "scope": scope or "default",
            "org_id": org_id,
            "user_id": user_id,
        }

    @staticmethod
    def _hash_content(content: str) -> str:
        import hashlib

        return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_memory_write_tool(**kwargs: Any) -> MemoryWriteTool:
    return MemoryWriteTool(**kwargs)
