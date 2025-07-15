"""Tests for NodeIndex basic add/search functionality with monkeypatched embedder."""

from __future__ import annotations

import sys
import types

# ---------------------------------------------------------------------------
# Stub embedding provider so NodeIndex can obtain an embedder ---------------
# ---------------------------------------------------------------------------
# Dummy embedder defined below using typing.SimpleNamespace after patch.

dummy_embedder = types.SimpleNamespace(embed_text=lambda text: _dummy_vector(text))

embed_mod = types.ModuleType("ice_sdk.providers.embedding")
embed_mod.get_default_embedder = lambda: dummy_embedder  # type: ignore[attr-defined]
sys.modules["ice_sdk.providers.embedding"] = embed_mod

from ice_sdk.providers.vector.node_index import NodeIndex


def _dummy_vector(label: str) -> list[float]:
    """Return a simple 3-d one-hot vector based on *label* substring."""
    if "A" in label:
        return [1.0, 0.0, 0.0]
    if "B" in label:
        return [0.0, 1.0, 0.0]
    return [0.0, 0.0, 1.0]


def test_node_index_roundtrip(monkeypatch):  # noqa: D103 – simple test
    # Monkey-patch default embedder with dummy deterministic vectors ---------
    dummy_embedder = types.SimpleNamespace(embed_text=_dummy_vector)
    monkeypatch.setattr(
        "ice_sdk.providers.vector.node_index.get_default_embedder",  # target to patch
        lambda: dummy_embedder,
    )

    ni = NodeIndex(dim=3)
    ni.add_node("nodeA", "tool")
    ni.add_node("nodeB", "ai")
    ni.build(n_trees=1)

    result = ni.search("nodeA", k=1)
    assert result == ["nodeA"]
