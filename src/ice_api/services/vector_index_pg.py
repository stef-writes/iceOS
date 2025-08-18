from __future__ import annotations

"""PgVector-backed vector index implementation.

This service implements the :class:`ice_core.protocols.vector.IVectorIndex`
protocol using the `semantic_memory` table and pgvector similarity search.

It delegates storage and retrieval to the typed repository functions in
`ice_api.services.semantic_memory_repository`.
"""

import hashlib
import os
from typing import Any, Dict, List, Tuple

from ice_core.protocols.vector import IVectorIndex

from .semantic_memory_repository import insert_semantic_entry, search_semantic


class PgVectorIndex(IVectorIndex):
    """Vector index backed by Postgres + pgvector.

    Args:
        embedding_dimension: Fixed vector dimensionality (defaults from env
            ICEOS_EMBEDDINGS_DIM or 1536)

    Example:
        >>> index = PgVectorIndex()
        >>> import anyio
        >>> async def _demo():
        ...     v = [1.0] + [0.0]*1535
        ...     await index.upsert("kb", "doc1", v, model_version="test")
        ...     res = await index.query("kb", v, k=1)
        ...     return res and res[0][0] == "doc1"
        >>> anyio.run(_demo)
        True
    """

    def __init__(self, embedding_dimension: int | None = None) -> None:
        dim_env = os.getenv("ICEOS_EMBEDDINGS_DIM")
        if embedding_dimension is None:
            try:
                self._dim = int(dim_env) if dim_env else 1536
            except Exception:
                self._dim = 1536
        else:
            self._dim = embedding_dimension

    # ------------------------------------------------------------------
    # Structural metadata
    # ------------------------------------------------------------------
    @property
    def embedding_dimension(self) -> int:  # noqa: D401
        """Fixed vector size handled by this index."""

        return self._dim

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------
    async def upsert(
        self,
        scope: str,
        key: str,
        embedding: List[float],
        *,
        model_version: str,
        dedup: bool = False,
    ) -> None:
        """Insert or update a vector for (scope, key).

        If ``dedup`` is True, unique constraint is enforced via ``content_hash``.
        For compatibility with existing schema, we derive a deterministic content
        hash from (scope, key, model_version).
        """

        self.validate_embedding(embedding)

        # Derive deterministic content hash; schema enforces uniqueness on this
        h = hashlib.sha256(f"{scope}:{key}:{model_version}".encode()).hexdigest()
        await insert_semantic_entry(
            scope=scope,
            key=key,
            content_hash=h,
            meta_json={},
            embedding_vec=embedding,
            org_id=None,
            user_id=None,
            model_version=model_version,
        )

    async def query(
        self,
        scope: str,
        embedding: List[float],
        *,
        k: int = 5,
        filter: Dict[str, Any] | None = None,
    ) -> List[Tuple[str, float]]:
        """Query nearest neighbors by cosine similarity.

        Returns a list of (key, similarity) tuples sorted by similarity desc.
        Optional filter may include ``org_id`` to scope results.
        """

        self.validate_embedding(embedding)
        org_id = (filter or {}).get("org_id") if filter else None
        rows = await search_semantic(
            scope=scope, query_vec=embedding, limit=k, org_id=org_id
        )
        out: List[Tuple[str, float]] = []
        for r in rows:
            out.append((str(r.get("key")), float(r.get("cosine_similarity", 0.0))))
        return out
