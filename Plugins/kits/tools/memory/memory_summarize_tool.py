from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import Field

from ice_core.base_tool import ToolBase


class MemorySummarizeTool(ToolBase):
    name: str = "memory_summarize_tool"
    description: str = Field(
        "Summarize recent semantic entries and write a summary entry with backlinks."
    )

    # Inputs (validated by _execute_impl signature):
    # - scope: str
    # - limit: int (how many recent to include)
    # - style: str (prompt hint)

    async def _execute_impl(
        self,
        *,
        scope: str = "kb",
        limit: int = 10,
        style: str = "concise",
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        from ice_api.services.semantic_memory_repository import (
            insert_semantic_entry,
            search_semantic,
        )

        # Use a trivial query vector made from a generic summary cue using hash embedder (deterministic)
        from ice_core.memory.embedders import get_embedder_from_env

        embedder = get_embedder_from_env()
        query_vec = await embedder.embed("summarize recent context")
        rows = await search_semantic(
            scope=scope, query_vec=query_vec, limit=limit, org_id=org_id
        )

        # Build a simple text summary; in future, call LLM for better results
        parts = [str(r.get("key")) for r in rows]
        summary_text = f"Summary ({style}) over {len(parts)} items: " + ", ".join(parts)

        # Write summary back with backlinks in metadata
        meta = {"backlinks": parts, "style": style}
        # Derive a content hash from keys to deduplicate
        import hashlib

        content_hash = hashlib.sha256(summary_text.encode()).hexdigest()
        sum_vec = await embedder.embed(summary_text)
        key = f"summary:{scope}:{content_hash[:12]}"
        _ = await insert_semantic_entry(
            scope=scope,
            key=key,
            content_hash=content_hash,
            meta_json=meta,
            embedding_vec=sum_vec,
            org_id=org_id,
            user_id=user_id,
            model_version="summary-v1",
        )
        return {"summary_key": key, "backlinks": parts}


def create_memory_summarize_tool(**kwargs: Any) -> MemorySummarizeTool:
    return MemorySummarizeTool(**kwargs)
