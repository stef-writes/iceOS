import pytest
from hypothesis import given, strategies as st

from ice_core.exceptions import DimensionMismatchError
from ice_core.memory.semantic import SemanticMemory
from ice_core.memory.base import MemoryConfig


@given(
    expected_dim=st.integers(min_value=32, max_value=1024),
    wrong_dim=st.integers(min_value=32, max_value=1024),
)
def test_validate_embedding_dimension(expected_dim: int, wrong_dim: int) -> None:
    """SemanticMemory must raise when embedding dimensionality differs."""

    # Ensure we are generating a *wrong* dimension
    assume_diff = pytest.assume if hasattr(pytest, "assume") else lambda x: None  # type: ignore
    assume_diff(expected_dim != wrong_dim)

    mem = SemanticMemory(MemoryConfig(enable_vector_search=True, embedding_dim=expected_dim))

    # Build a dummy vector of wrong_dim length
    vector = [0.0] * wrong_dim

    with pytest.raises(DimensionMismatchError):
        mem.validate_embedding(vector)  # type: ignore[attr-defined]
