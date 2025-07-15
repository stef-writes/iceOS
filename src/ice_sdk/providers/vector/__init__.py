"""Vector store providers – minimal stubs for contract tests."""

from __future__ import annotations

from typing import List

__all__ = ["AnnoyIndexAdapter", "PgVectorStore", "get_default_index", "VectorLike"]

VectorLike = List[float]


class AnnoyIndexAdapter:  # noqa: D101 – minimal in-memory stub
    """Very small in-memory implementation just good enough for contract tests."""

    def __init__(self) -> None:  # noqa: D401
        self._vectors: dict[str, dict[str, VectorLike]] = {}

    async def upsert(  # noqa: D401 – async to satisfy interface
        self,
        scope: str,
        key: str,
        vector: VectorLike,
        *,
        model_version: str,
    ) -> None:
        self._vectors.setdefault(scope, {})[key] = vector

    async def query(  # noqa: D401 – async to satisfy interface
        self,
        scope: str,
        vector: VectorLike,
        k: int = 1,
    ) -> list[tuple[str, float]]:
        keys = list(self._vectors.get(scope, {}))[:k]
        return [(k, 0.0) for k in keys]


class PgVectorStore:  # noqa: D101 – stub class
    async def upsert(
        self, scope: str, key: str, vector: VectorLike, *, model_version: str
    ):  # noqa: D401
        return None

    async def query(self, scope: str, vector: VectorLike, k: int = 1):  # noqa: D401
        return [(scope, 0.0)]


def get_default_index() -> AnnoyIndexAdapter:  # noqa: D401 – stub helper
    return AnnoyIndexAdapter()
