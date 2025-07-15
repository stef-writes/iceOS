"""Contract tests for ChromaDBAdapter."""

from __future__ import annotations

import pytest

pytest.importorskip("chromadb")

from ice_sdk.models.embedding import DEFAULT_DIM
from ice_sdk.providers.vector import get_default_index


@pytest.mark.asyncio
async def test_chroma_upsert_and_query():
    index = get_default_index()

    scope = "test_scope"
    key = "doc1"
    vector = [0.05] * DEFAULT_DIM

    await index.upsert(scope, key, vector, model_version="test-model")

    results = await index.query(scope, vector, k=1)
    assert results[0][0] == key
