from __future__ import annotations

"""Contract tests for AnnoyIndexAdapter."""

from unittest.mock import Mock, patch  # noqa: F401  # Consolidated helper imports

import pytest

from ice_sdk.models.embedding import DEFAULT_DIM
from ice_sdk.providers.vector.annoy import AnnoyIndexAdapter

pytest.importorskip("annoy")


@pytest.mark.asyncio
async def test_annoy_upsert_and_query():
    index = AnnoyIndexAdapter()

    scope = "test_scope"
    key = "doc1"
    vector = [0.1] * DEFAULT_DIM

    await index.upsert(scope, key, vector, model_version="test-model")

    results = await index.query(scope, vector, k=1)
    assert results  # at least one result
    assert results[0][0] == key
