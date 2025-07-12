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

    # ------------------------------------------------------------------
    # Synchronous vector-centric helpers (legacy compatibility) ----------
    # ------------------------------------------------------------------
    @abstractmethod
    def store(self, key: str, vector: List[float]) -> None:  # type: ignore[override]
        """Persist a raw *vector* with associated *key*.

        This synchronous variant is useful in lightweight unit-tests where
        an event-loop might not be available.  Concrete adapters should map
        the call to their underlying asynchronous implementation whenever
        possible so they remain the single source-of-truth.
        """

    @abstractmethod
    def recall(self, query: List[float], top_k: int = 5) -> List[str]:  # noqa: D401
        """Return up to *top_k* keys ranked by similarity against *query*."""


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

    # ------------------------------------------------------------------
    # Synchronous wrappers ---------------------------------------------
    # ------------------------------------------------------------------
    def store(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """No-op store – used by unit-tests exercising dependency injection."""

    def recall(self, *args: Any, **kwargs: Any) -> List[str]:  # type: ignore[override]
        """Always return an empty list to signify no stored vectors."""
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
            from typing import cast

            return cast(List[float], self.encoder.encode(text).tolist())  # type: ignore[arg-type]
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

    # ------------------------------------------------------------------
    # Synchronous vector API --------------------------------------------
    # ------------------------------------------------------------------
    def store(self, key: str, vector: List[float]) -> None:  # type: ignore[override]
        """Persist *vector* directly bypassing text encoding.

        This helper maps the synchronous signature onto the existing
        asynchronous storage logic while avoiding any event-loop juggling.
        """
        blob = sqlite3.Binary(json.dumps(vector).encode())
        with self.conn:
            self.conn.execute(
                "INSERT INTO memory (content, vector) VALUES (?, ?)", (key, blob)
            )

    def recall(self, query: List[float], top_k: int = 5) -> List[str]:  # noqa: D401
        rows = self.conn.execute("SELECT content, vector FROM memory").fetchall()
        scored: list[tuple[str, float]] = []
        for content, blob in rows:
            vec = json.loads(blob)
            score = self._cosine(query, vec)
            scored.append((content, score))
        scored.sort(key=lambda t: t[1], reverse=True)
        return [c for c, _ in scored[:top_k]]


# ----------------------------------------------------------------------
# Public re-exports -----------------------------------------------------
# ----------------------------------------------------------------------

__all__: list[str] = [
    "BaseMemory",
    "NullMemory",
    "SQLiteVectorMemory",
]
