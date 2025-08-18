from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from ice_api.services.semantic_memory_repository import insert_semantic_entry
from ice_core.base_tool import ToolBase
from ice_core.memory.embedders import get_embedder_from_env
from ice_core.protocols.tool import ToolConfig
from ice_core.registry import registry
from ice_core.validation.validated_protocol import validated_protocol


@dataclass
class IngestionInputs:
    source_type: str  # "url" | "file" | "text"
    source: str
    scope: str = "kb"
    chunk_size: int = 1000
    overlap: int = 200
    metadata: Optional[Dict[str, Any]] = None
    org_id: Optional[str] = None
    user_id: Optional[str] = None


def _chunk(text: str, size: int, overlap: int) -> List[str]:
    if size <= 0:
        return [text]
    chunks: List[str] = []
    i = 0
    step = max(1, size - overlap)
    while i < len(text):
        chunks.append(text[i : i + size])
        i += step
    return chunks


class IngestionTool(ToolBase):
    name = "ingestion_tool"
    description = (
        "Ingest URL/file/text into semantic memory with chunking and embeddings."
    )

    @validated_protocol
    async def run(
        self, inputs: Dict[str, Any], config: ToolConfig | None = None
    ) -> Dict[str, Any]:
        args = IngestionInputs(**inputs)
        # Fetch content
        if args.source_type == "url":
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(args.source)
                resp.raise_for_status()
                content = resp.text
        elif args.source_type == "file":
            base_dir = os.getenv("ICE_INGEST_BASE", "/app/data")
            path = os.path.join(base_dir, args.source)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        elif args.source_type == "text":
            content = args.source
        else:
            return {"error": f"unsupported source_type {args.source_type}"}

        embedder = get_embedder_from_env()
        tasks: List[asyncio.Task[None]] = []
        results: List[Dict[str, Any]] = []

        async def _process_chunk(idx: int, text: str) -> None:
            vec = await embedder.embed(text)
            key = f"ingest:{idx}:{hash(text)}"
            row_id = await insert_semantic_entry(
                scope=args.scope,
                key=key,
                content_hash=str(hash(text)),
                meta_json=args.metadata or {},
                embedding_vec=vec,
                org_id=args.org_id,
                user_id=args.user_id,
                model_version=os.getenv(
                    "ICEOS_EMBEDDINGS_MODEL", "text-embedding-3-small"
                ),
            )
            results.append({"key": key, "row_id": row_id})

        for i, ch in enumerate(_chunk(content, args.chunk_size, args.overlap)):
            tasks.append(asyncio.create_task(_process_chunk(i, ch)))
        if tasks:
            await asyncio.gather(*tasks)
        return {"ingested": results}


def create_ingestion_tool() -> IngestionTool:
    return IngestionTool()


# Register factory for dev convenience
registry.register_tool_factory("ingestion_tool", __name__ + ":create_ingestion_tool")
