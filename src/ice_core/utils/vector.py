"""Utility helpers for vector operations.

Currently provides dimensionality validation to enforce safety invariants.
"""

from __future__ import annotations

from typing import Sequence

from ice_core.exceptions import DimensionMismatchError


def validate_embedding_dimension(
    embedding: Sequence[float], expected_dimension: int
) -> None:
    """Validate that *embedding* has *expected_dimension* elements.

    Args:
        embedding: Sequence of floats representing the vector embedding.
        expected_dimension: Expected dimensionality.

    Raises:
        DimensionMismatchError: If the actual dimension differs from *expected_dimension*.

    Example:
        >>> validate_embedding_dimension([0.1, 0.2], 2)
        # passes silently
        >>> validate_embedding_dimension([0.1, 0.2, 0.3], 2)
        # Traceback (most recent call last):
        #   ...
        # ice_core.exceptions.DimensionMismatchError: Embedding dimension mismatch: expected 2, got 3
    """

    actual = len(embedding)
    if actual != expected_dimension:
        raise DimensionMismatchError(expected_dimension, actual)
