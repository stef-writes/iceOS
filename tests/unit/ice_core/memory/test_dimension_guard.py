"""Unit tests for `SemanticMemory.validate_embedding` with *deterministic* inputs.

The original version used Hypothesis; we replace it with explicit cases to
avoid the extra dependency while still exercising the same semantics.
"""

from __future__ import annotations

import pytest

from ice_core.exceptions import DimensionMismatchError
from ice_core.memory.memory_base_protocol import MemoryConfig
from ice_core.memory.semantic_memory_store import SemanticMemory


def test_validate_embedding_dimension_passes() -> None:
    """No exception when vector length matches configured dimension."""

    mem = SemanticMemory(MemoryConfig(enable_vector_search=True, embedding_dim=64))
    vector = [0.0] * 64
    mem.validate_embedding(vector)  # Should **not** raise


def test_validate_embedding_dimension_mismatch() -> None:
    """Raise `DimensionMismatchError` on length mismatch."""

    mem = SemanticMemory(MemoryConfig(enable_vector_search=True, embedding_dim=32))
    wrong_vector = [0.0] * 16
    with pytest.raises(DimensionMismatchError):
        mem.validate_embedding(wrong_vector)  # type: ignore[attr-defined]
