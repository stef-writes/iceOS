"""NodeIndex – lightweight vector index for blueprint nodes.

This provider embeds the concatenation of a node's **id**, **type** and
(optional) **prompt / description** using the default *EmbeddingProvider*
and stores the vectors in an Annoy index for fast cosine-similarity search.

Only the *index owner* process mutates the Annoy index; read-only queries
are safe across threads.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List

from annoy import AnnoyIndex  # type: ignore

try:
    from ice_sdk.providers.embedding import get_default_embedder  # type: ignore
except ImportError:  # pragma: no cover – fallback to new API
    from ice_sdk.providers.embedding import get_embedder as get_default_embedder

_DIM = 768  # OpenAI/Tiny embed size – adjust if another embedder used


class NodeIndex:
    """In-memory Annoy vector index over Node metadata."""

    def __init__(self, dim: int = _DIM) -> None:
        self._dim = dim
        self._index = AnnoyIndex(dim, "angular")
        self._id_lookup: list[str] = []
        self._temp_dir = Path(tempfile.mkdtemp(prefix="node_index_"))
        self._index_path = self._temp_dir / "nodes.ann"
        # Obtain embedder via indirection so tests can monkey-patch this helper
        self._embedder = get_default_embedder()

    # ------------------------------------------------------------------
    # Index construction ------------------------------------------------
    # ------------------------------------------------------------------
    def add_node(
        self, node_id: str, node_type: str, description: str | None = None
    ) -> None:
        """Add/overwrite *node_id* vector in the index."""
        text_parts = [node_id, node_type]
        if description:
            text_parts.append(description)
        vector = self._embedder.embed_text("\n".join(text_parts))
        if len(vector) != self._dim:
            raise ValueError(
                "Embed size mismatch – configure NodeIndex with correct dim"
            )
        idx = self._ensure_annoy_id(node_id)
        self._index.add_item(idx, vector)

    def _ensure_annoy_id(self, node_id: str) -> int:
        try:
            return self._id_lookup.index(node_id)
        except ValueError:
            self._id_lookup.append(node_id)
            return len(self._id_lookup) - 1

    def build(self, n_trees: int = 10) -> None:
        """(Re)build the Annoy index with *n_trees*."""
        if self._index.get_n_items() == 0:
            return
        self._index.build(n_trees)
        self._index.save(str(self._index_path))

    # ------------------------------------------------------------------
    # Query -----------------------------------------------------------------
    # ------------------------------------------------------------------
    def search(self, query: str, k: int = 5) -> List[str]:
        """Return up to *k* node_ids most similar to *query*."""
        vector = self._embedder.embed_text(query)
        ids: list[int] = self._index.get_nns_by_vector(vector, k)
        return [self._id_lookup[i] for i in ids]
