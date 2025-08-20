from __future__ import annotations

import asyncio
import hashlib
import os
from typing import Any, Dict, List, Optional

import httpx

from ice_api.services.semantic_memory_repository import insert_semantic_entry
from ice_core.base_tool import ToolBase
from ice_core.memory.embedders import get_embedder_from_env
from ice_core.registry import registry


class IngestionInputs:
    def __init__(
        self,
        *,
        source_type: str,
        source: str,
        scope: str = "kb",
        chunk_size: int = 1000,
        overlap: int = 200,
        metadata: Optional[Dict[str, Any]] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        self.source_type = source_type
        self.source = source
        self.scope = scope
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.metadata = metadata
        self.org_id = org_id
        self.user_id = user_id


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
    name: str = "ingestion_tool"
    description: str = (
        "Ingest URL/file/text into semantic memory with chunking and embeddings."
    )

    async def _execute_impl(
        self,
        *,
        source_type: str,
        source: str,
        scope: str = "kb",
        chunk_size: int = 1000,
        overlap: int = 200,
        metadata: Optional[Dict[str, Any]] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        args = IngestionInputs(
            source_type=source_type,
            source=source,
            scope=scope,
            chunk_size=chunk_size,
            overlap=overlap,
            metadata=metadata,
            org_id=org_id,
            user_id=user_id,
        )
        # Fetch content
        if args.source_type == "url":
            # Basic safety: allowed schemes and size cap
            if not (
                args.source.startswith("http://") or args.source.startswith("https://")
            ):
                return {"error": "unsupported URL scheme"}
            async with httpx.AsyncClient(timeout=20.0) as client:
                # simple exponential backoff for transient failures
                last_exc: Exception | None = None
                for attempt in range(4):
                    try:
                        resp = await client.get(args.source)
                        resp.raise_for_status()
                        break
                    except Exception as exc:
                        last_exc = exc
                        await asyncio.sleep(0.2 * (2**attempt))
                else:
                    assert last_exc is not None
                    raise last_exc
                ctype = resp.headers.get("content-type", "")
                if not (ctype.startswith("text/") or "json" in ctype):
                    return {"error": f"disallowed content-type: {ctype}"}
                raw = resp.content
                max_bytes = int(os.getenv("ICE_INGEST_MAX_BYTES", "5242880"))
                if len(raw) > max_bytes:
                    return {"error": f"document too large: {len(raw)} bytes"}
                content = raw.decode("utf-8", errors="ignore")
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
            key = f"_ing:{idx}:{hashlib.sha256(text.encode()).hexdigest()[:12]}"
            row_id = await insert_semantic_entry(
                scope=args.scope,
                key=key,
                content_hash=hashlib.sha256(text.encode()).hexdigest(),
                meta_json={**(args.metadata or {}), "content": text},
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
