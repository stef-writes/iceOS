from __future__ import annotations

from typing import Protocol, runtime_checkable

from ice_sdk.models.embedding import Embedding


@runtime_checkable
class IEmbedder(Protocol):
    """Minimal contract for embedder implementations."""

    async def embed(self, text: str) -> Embedding: ...

    def estimate_cost(self, text: str) -> float: ...
