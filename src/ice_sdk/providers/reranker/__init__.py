"""Reranker providers (stub)."""

from __future__ import annotations

__all__ = ["get_default_reranker"]


class _DefaultReranker:  # noqa: D101 – stub
    async def rerank(self, items: list[str]) -> list[str]:  # noqa: D401 – stub
        return items[::-1]


def get_default_reranker() -> _DefaultReranker:  # noqa: D401 – stub
    return _DefaultReranker()
