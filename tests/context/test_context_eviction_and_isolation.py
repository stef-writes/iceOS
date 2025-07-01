import asyncio

import pytest

from ice_sdk.context.manager import GraphContextManager


@pytest.mark.asyncio
async def test_concurrent_contexts_isolation():
    """Two concurrent sessions must not share GraphContext objects."""
    mgr = GraphContextManager(max_sessions=5)

    async def _get_ctx(sess_id: str):
        return mgr.get_context(session_id=sess_id)

    ctx_a, ctx_b = await asyncio.gather(_get_ctx("sessA"), _get_ctx("sessB"))

    # Ensure non-null ----------------------------------------------------
    assert ctx_a is not None and ctx_b is not None
    assert ctx_a.session_id == "sessA"
    assert ctx_b.session_id == "sessB"
    # Distinct objects ---------------------------------------------------
    assert ctx_a is not ctx_b


def test_lru_eviction_of_old_sessions():
    """Oldest session should be evicted once *max_sessions* is exceeded."""
    mgr = GraphContextManager(max_sessions=2)

    c1 = mgr.get_context(session_id="s1")
    c2 = mgr.get_context(session_id="s2")
    # Both contexts tracked ------------------------------------------------
    assert list(mgr._contexts.keys()) == ["s1", "s2"]

    c3 = mgr.get_context(session_id="s3")
    # LRU eviction should have dropped "s1"
    assert "s1" not in mgr._contexts
    assert list(mgr._contexts.keys()) == ["s2", "s3"]
    assert len(mgr._contexts) == 2

    # Fetching s1 again yields a *new* context instance --------------------
    c1_new = mgr.get_context(session_id="s1")
    assert c1_new is not c1
