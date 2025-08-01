"""Lightweight in-process memory adapters for context management.

This module provides a *minimal* `BaseMemory` interface plus a no-op
`NullMemory` implementation suitable for most stateless workflows.

This is specifically for context management (short-term execution state),
not for long-term memory persistence. For long-term memory, use the
core memory system from `ice_core.memory`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List


class BaseMemory(ABC):
    """Abstract interface for chat / tool memory adapters."""

    # ------------------------------------------------------------------
    # Async API ---------------------------------------------------------
    # ------------------------------------------------------------------

    @abstractmethod
    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> None:  # noqa: D401 – simple doc
        """Persist *content* and optional *metadata*."""

    @abstractmethod
    async def retrieve(self, query: str, k: int = 5) -> List[str]:  # noqa: D401 – simple doc
        """Return up-to-*k* items relevant to *query*."""

    # ------------------------------------------------------------------
    # Optional synchronous vector API (no-op default) -------------------
    # ------------------------------------------------------------------

    def store(self, key: str, vector: List[float]) -> None:  # pragma: no cover – default stub
        """Persist *vector* under *key* (no-op default)."""

    def recall(self, vector: List[float], top_k: int = 5) -> List[str]:  # pragma: no cover – default stub
        """Return up-to-*top_k* keys similar to *vector* (no-op default)."""
        return []

class NullMemory(BaseMemory):
    """A no-operation memory adapter.

    This implementation fulfils the interface contract while deliberately
    discarding all data – useful when long-term memory is not required.
    """

    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> None:  # noqa: D401 – simple doc
        return None

    async def retrieve(self, query: str, k: int = 5) -> List[str]:  # noqa: D401 – simple doc
        return []

__all__: list[str] = [
    "BaseMemory",
    "NullMemory",
]
