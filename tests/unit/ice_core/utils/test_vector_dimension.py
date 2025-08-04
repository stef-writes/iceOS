import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from ice_core.exceptions import DimensionMismatchError
from ice_core.utils.vector import validate_embedding_dimension


@given(st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1, max_size=20))
def test_validate_passes_for_correct_dimension(vec):
    """Validation must pass when embedding length equals expected."""
    validate_embedding_dimension(vec, len(vec))  # Should not raise


@given(
    st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1, max_size=20),
    st.integers(min_value=1, max_value=20),
)
def test_validate_raises_on_mismatch(vec, dim):
    """Validation must raise DimensionMismatchError when dimension mismatches."""
    assume(dim != len(vec))
    with pytest.raises(DimensionMismatchError):
        validate_embedding_dimension(vec, dim)
