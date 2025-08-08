"""Test that non-serialisable values raise SerializationError in context manager."""

from __future__ import annotations

import pytest

from ice_core.exceptions import SerializationError
from ice_orchestrator.context.manager import GraphContextManager


class _Dummy:
    pass


def test_serialization_guard() -> None:
    ctx_mgr = GraphContextManager(max_tokens=1000)

    with pytest.raises(SerializationError):
        ctx_mgr.update_node_context(node_id="n1", content={"bad": _Dummy()})
