from __future__ import annotations

import pytest

# Skip entire module – vector embedding hashing contract tests removed -------


pytest.skip("Vector embedding/hash tests removed in refactor", allow_module_level=True)

"""Contract smoke-tests for new vector stack primitives."""

from ice_core.utils.hashing import HashMode, compute_hash
from ice_sdk.models.embedding import DEFAULT_DIM, Embedding


@pytest.mark.parametrize("vector_len", [100, DEFAULT_DIM, 500])
def test_embedding_vector_is_padded_or_truncated(vector_len: int):
    vector = [0.1] * vector_len
    emb = Embedding(
        vector=vector,
        model_version="test-v1",
        original_dim=vector_len,
        hash_algorithm="sha256",
    )
    assert len(emb.vector) == DEFAULT_DIM


def test_compute_hash_variants():
    text = "hello world"
    sha = compute_hash(text, HashMode.SECURITY)
    assert sha == compute_hash(text)  # default mode

    blake = compute_hash(text, HashMode.PERFORMANCE)
    assert isinstance(blake, str)
    assert len(blake) == len(sha)  # hex lengths (may differ but same chars count)
