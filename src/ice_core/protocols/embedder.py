"""Embedder protocol definition."""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol


class IEmbedder(Protocol):
    """Protocol for text embedding implementations."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Convert text to vector embedding.

        Args:
            text: Text to embed

        Returns:
            Vector embedding as list of floats
        """
        ...

    @abstractmethod
    def estimate_cost(self, text: str) -> float:
        """Estimate the cost of embedding the given text.

        Args:
            text: Text to estimate cost for

        Returns:
            Estimated cost in USD
        """
        ...
