"""Embedding providers (stub)."""

from __future__ import annotations

from ice_sdk.models.embedding import DEFAULT_DIM, Embedding

__all__ = ["get_embedder"]


class _DefaultEmbedder:  # noqa: D101 – stub class
    async def embed(self, text: str) -> Embedding:  # noqa: D401 – stub
        return Embedding(vector=[0.1] * DEFAULT_DIM)

    # Compatibility shim for older callers expecting a synchronous method
    def embed_text(self, text: str) -> list[float]:  # noqa: D401 – stub
        """Synchronous helper returning raw vector list (test-only)."""
        return [0.1] * DEFAULT_DIM


def get_embedder(name: str | None = None) -> _DefaultEmbedder:  # noqa: D401 – stub
    return _DefaultEmbedder()
