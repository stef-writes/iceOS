"""Vector index protocol definition."""
from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, List, Protocol, Tuple


class IVectorIndex(Protocol):
    """Protocol for vector index implementations."""
    
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