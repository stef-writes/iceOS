"""Vector index protocol definition."""
from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, List, Protocol, Tuple


from ice_core.exceptions import DimensionMismatchError

class IVectorIndex(Protocol):
    """Vector index protocol ensuring dimensional safety and search consistency."""

    # ------------------------------------------------------------------
    # Structural metadata
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Fixed dimensionality of vectors handled by this index."""
        ...

    # ------------------------------------------------------------------
    # Helper – default dimensionality guard
    # ------------------------------------------------------------------

    def validate_embedding(self, embedding: list[float]) -> None:  # noqa: D401
        """Raise :class:`DimensionMismatchError` if *embedding* has wrong length."""
        expected = self.embedding_dimension
        actual = len(embedding)
        if actual != expected:
            raise DimensionMismatchError(expected, actual)
    
    @abstractmethod
    async def upsert(
        self,
        scope: str,
        key: str,
        embedding: List[float],
        *,
        model_version: str,
        dedup: bool = False,
    ) -> None:
        """Insert or update a vector.
        
        Args:
            scope: Namespace for the vector
            key: Unique identifier
            embedding: The vector embedding
            model_version: Version of the embedding model
            dedup: Whether to deduplicate
        """
        ...
    
    @abstractmethod
    async def query(
        self,
        scope: str,
        embedding: List[float],
        *,
        k: int = 5,
        filter: Dict[str, Any] | None = None,
    ) -> List[Tuple[str, float]]:
        """Query for similar vectors.
        
        Args:
            scope: Namespace to search in
            embedding: Query vector
            k: Number of results to return
            filter: Optional metadata filters
            
        Returns:
            List of (key, similarity_score) tuples
        """
        ... 