"""Unified Knowledge Service – lightweight document processing & retrieval.

This is **phase-1** implementation providing the public API surface needed by
``EnterpriseKBNode``.  The vector search is backed by *ChromaDBAdapter* with a
very thin wrapper that stores chunk metadata in-memory.  A follow-up roadmap
will add persistent metadata & granular ACLs but the current iteration keeps
all state process-local which is sufficient for CI and unit tests.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator

from ice_core.utils.text import TextProcessor
from ice_sdk.providers.embedding import get_embedder
from ice_sdk.providers.vector.chroma import ChromaDBAdapter

__all__ = [
    "KnowledgeConfig",
    "KnowledgeService",
]


class KnowledgeConfig(BaseModel):
    """Configuration model for :class:`KnowledgeService`."""

    watch_dirs: List[str] = Field(
        default_factory=list, description="Directories to watch for documents"
    )
    auto_parse: bool = Field(
        default=True, description="Automatically parse existing docs on start-up"
    )
    chunk_size: int = Field(
        default=1000, ge=100, description="Chunk size in tokens/words"
    )
    chunk_overlap: int = Field(
        default=200, ge=0, description="Token/word overlap between chunks"
    )

    @field_validator("chunk_overlap")  # pyright: ignore[reportGeneralTypeIssues]
    @classmethod
    def _validate_overlap(cls, v: int, info: Any) -> int:  # noqa: D401 – validator
        if v >= info.data.get("chunk_size", 1000):
            raise ValueError("chunk_overlap must be < chunk_size")
        return v


class KnowledgeService:
    """High-level API for document ingestion & semantic retrieval."""

    _ID_DELIM = "::"  # stable delimiter for key → file#idx mapping

    def __init__(self, config: KnowledgeConfig):
        self.config = config
        # Propagate chunk sizing defaults into TextProcessor to satisfy strict typing
        self._text_processor = TextProcessor(
            default_chunk_size=config.chunk_size,
            default_chunk_overlap=config.chunk_overlap,
        )
        self._vector_index = ChromaDBAdapter()
        self._embedder = get_embedder()
        self._collection = "enterprise_kb"
        # In-memory mapping of chunk-id → (text, metadata)
        self._chunk_lookup: Dict[str, Dict[str, Any]] = {}

        # Optionally ingest existing documents --------------------------
        if config.auto_parse:
            for doc_dir in self.config.watch_dirs:
                self._process_directory(Path(doc_dir))

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    # ------------------------------------------------------------------
    async def query(
        self, text: str, n_results: int = 5
    ) -> List[Dict[str, Any]]:  # noqa: D401
        """Return *n_results* semantically closest chunks for *text*."""

        if not text.strip():
            return []

        # 1. Embed query ------------------------------------------------
        # Prefer sync helper if available to avoid nested event-loops
        if hasattr(self._embedder, "embed_text"):
            query_vec: List[float] = self._embedder.embed_text(text)  # type: ignore[attr-defined]
            model_version = "default"
        else:  # pragma: no cover – remote provider path
            emb = await self._embedder.embed(text)  # type: ignore[attr-defined]
            query_vec = emb.vector
            model_version = emb.model_version

        # 2. Vector search ---------------------------------------------
        hits = await self._vector_index.query(
            scope=self._collection,
            embedding=query_vec,
            k=n_results,
        )

        # 3. Materialise results ---------------------------------------
        results: list[dict[str, Any]] = []
        for key, distance in hits:
            chunk = self._chunk_lookup.get(key)
            if not chunk:
                continue  # pragma: no cover – stale vector, should not happen
            results.append(
                {
                    "document": chunk["text"],
                    "metadata": chunk["metadata"],
                    "distance": distance,
                    "embedding_model": model_version,
                }
            )
        return results

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------
    def _process_directory(self, path: Path) -> None:  # noqa: D401
        """Recursively ingest all supported documents under *path*."""

        if not path.exists():
            return
        for ext in ("*.md", "*.txt", "*.pdf", "*.docx"):
            for file_path in path.rglob(ext):
                self._process_file(file_path)

    def _process_file(self, file_path: Path) -> None:  # noqa: D401
        """Extract, chunk & upsert a *single* document synchronously."""

        try:
            content = self._text_processor.extract_text(file_path)
        except Exception as exc:  # pragma: no cover – failed extraction
            # We swallow and log extraction failures so that ingestion pipeline
            # continues with other files.
            import logging

            logging.getLogger(__name__).warning(
                "Failed to extract %s – %s", file_path, exc
            )
            return

        chunks = self._text_processor.chunk_text(
            content, self.config.chunk_size, self.config.chunk_overlap
        )
        if not chunks:
            return

        # ------------------------------------------------------------------
        # Embed + upsert in *blocking* mode to avoid nested event-loops.
        # ------------------------------------------------------------------
        loop = asyncio.get_event_loop()
        for idx, chunk_text in enumerate(chunks):
            key = f"{file_path}{self._ID_DELIM}{idx}"
            embedding_vec: List[float]
            model_version: str
            if hasattr(self._embedder, "embed_text"):
                embedding_vec = self._embedder.embed_text(chunk_text)  # type: ignore[attr-defined]
                model_version = "default"
            else:  # pragma: no cover – remote provider path
                emb = loop.run_until_complete(self._embedder.embed(chunk_text))  # type: ignore[attr-defined]
                embedding_vec = emb.vector
                model_version = emb.model_version

            loop.run_until_complete(
                self._vector_index.upsert(
                    scope=self._collection,
                    key=key,
                    embedding=embedding_vec,
                    model_version=model_version,
                )
            )

            # Update in-mem lookup after successful upsert --------------
            self._chunk_lookup[key] = {
                "text": chunk_text,
                "metadata": {"source": str(file_path)},
            }
