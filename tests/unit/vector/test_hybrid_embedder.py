"""Tests for HybridEmbedder functionality."""

from __future__ import annotations

import pytest

pytest.importorskip("sentence_transformers")

from ice_sdk.models.embedding import DEFAULT_DIM
from ice_sdk.providers.embedding import get_embedder


@pytest.mark.asyncio
async def test_hybrid_embedder_local_path(monkeypatch):
    # Force router to local only to ensure fast path
    embedder = get_embedder()
    embedder._router_order = ["local"]  # type: ignore[attr-defined]

    emb = await embedder.embed("hello world")
    assert len(emb.vector) == DEFAULT_DIM
    assert emb.model_version.startswith("sentence-transformers::")


@pytest.mark.asyncio
async def test_hybrid_embedder_cost_estimate():
    embedder = get_embedder()
    cost = embedder.estimate_cost("quick brown fox")
    assert cost >= 0.0
