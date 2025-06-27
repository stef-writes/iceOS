from __future__ import annotations

import tempfile

from ice_sdk.context.manager import GraphContext, GraphContextManager
from ice_sdk.context.store import ContextStore


def test_update_node_context_truncates_long_payload(tmp_path):
    """When *max_tokens* is tiny, the stored context should be truncated."""

    # Create an isolated on-disk store inside pytest's tmpdir -----------
    store_path = tmp_path / "ctx.json"
    store = ContextStore(context_store_path=str(store_path))

    mgr = GraphContextManager(max_tokens=1, store=store)  # ⇒ ≈4-char char_budget
    mgr.set_context(GraphContext(session_id="sess-test"))

    long_text = "x" * 100  # clearly exceeds 4-char budget
    mgr.update_node_context("node", long_text)

    persisted = mgr.store.get("node")

    assert isinstance(persisted, str)
    assert len(persisted) <= 4  # budget enforced
    assert persisted == long_text[:4] 