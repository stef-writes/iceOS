"""Tests for `ice_core.utils.vector.validate_embedding_dimension` without Hypothesis."""

from __future__ import annotations

import pytest

from ice_core.exceptions import DimensionMismatchError
from ice_core.utils.vector import validate_embedding_dimension


def test_validate_passes_for_correct_dimension() -> None:
    vec = [0.1, 0.2, 0.3, 0.4]
    validate_embedding_dimension(vec, len(vec))  # Should not raise


def test_validate_raises_on_mismatch() -> None:
    vec = [0.1, 0.2, 0.3]
    with pytest.raises(DimensionMismatchError):
        validate_embedding_dimension(vec, len(vec) + 2)
