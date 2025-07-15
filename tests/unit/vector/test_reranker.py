"""Tests for MiniLMCrossEncoderReranker."""

from __future__ import annotations

import pytest

pytest.importorskip("sentence_transformers")

from ice_sdk.providers.reranker import get_default_reranker


@pytest.mark.asyncio
async def test_mini_lm_rerank_order():
    reranker = get_default_reranker()

    query = "capital of france"
    docs = [
        ("doc1", 0.5, "Paris is the capital and most populous city of France."),
        ("doc2", 0.4, "Berlin is the capital of Germany."),
    ]

    out = await reranker.rerank(query, docs)
    assert out[0][0] == "doc1"
