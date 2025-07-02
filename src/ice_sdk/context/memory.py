"""Pluggable memory adapters for agent reflection and retrieval."""

from __future__ import annotations

import json
import math
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Tuple

# Optional – leverage *sentence-transformers* when available -----------------
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except ImportError:  # pragma: no cover – fallback when dependency missing
    SentenceTransformer = None  # type: ignore


class BaseMemory(ABC):
    """Abstract base class for pluggable memory back-ends."""

    @abstractmethod
    async def add(
        self, content: str, metadata: dict[str, Any] | None = None
    ) -> None:  # noqa: D401
        """Persist *content* in memory."""

    @abstractmethod
    async def retrieve(
        self, query: str, k: int = 5
    ) -> List[Tuple[str, float]]:  # noqa: D401
        """Return top-*k* ``(content, score)`` pairs ranked by similarity."""


class NullMemory(BaseMemory):
    """No-op adapter used as default when no memory is configured."""

    async def add(
        self, content: str, metadata: dict[str, Any] | None = None
    ) -> None:  # noqa: D401
        return None

    async def retrieve(
        self, query: str, k: int = 5
    ) -> List[Tuple[str, float]]:  # noqa: D401
        return []


class SQLiteVectorMemory(BaseMemory):
    """Lightweight vector store backed by SQLite.

    Embedding model defaults to ``all-MiniLM-L6-v2`` from *sentence-transformers*
    when the package is available.  Otherwise, a naive character-level encoding
    is used – *good enough* for rapid prototyping.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.conn = sqlite3.connect(str(db_path))
        self._init_schema()
        self.encoder = None
        if SentenceTransformer:
            try:
                self.encoder = SentenceTransformer("all-MiniLM-L6-v2")  # type: ignore[arg-type]
            except Exception:  # pragma: no cover – defensive
                self.encoder = None

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    # ------------------------------------------------------------------
    async def add(
        self, content: str, metadata: dict[str, Any] | None = None
    ) -> None:  # noqa: D401
        vector = self._encode(content)
        blob = sqlite3.Binary(json.dumps(vector).encode())
        with self.conn:
            self.conn.execute(
                "INSERT INTO memory (content, vector) VALUES (?, ?)", (content, blob)
            )

    async def retrieve(
        self, query: str, k: int = 5
    ) -> List[Tuple[str, float]]:  # noqa: D401
        q_vec = self._encode(query)
        rows = self.conn.execute("SELECT content, vector FROM memory").fetchall()
        scored: list[tuple[str, float]] = []
        for content, blob in rows:
            vec = json.loads(blob)
            score = self._cosine(q_vec, vec)
            scored.append((content, score))
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:k]

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        with self.conn:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, vector BLOB)"
            )

    def _encode(self, text: str) -> List[float]:
        if self.encoder:
            return self.encoder.encode(text).tolist()  # type: ignore[return-value]
        # Fallback: very naive char-based encoding (bounded to 128 chars)
        return [ord(c) / 256 for c in text[:128]]

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        size = min(len(a), len(b))
        dot = sum(a[i] * b[i] for i in range(size))
        denom = math.sqrt(sum(x * x for x in a[:size])) * math.sqrt(
            sum(x * x for x in b[:size])
        )
        return dot / denom if denom else 0.0
