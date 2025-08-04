"""Basic unit test for new EventBus pub-sub mechanism."""
from __future__ import annotations

from typing import Any, Dict

from ice_orchestrator.execution.event_bus import EventBus


def test_event_bus_pub_sub() -> None:
    received: dict[str, Dict[str, Any]] = {}

    def _collector(topic: str, payload: Dict[str, Any]) -> None:  # noqa: D401
        received[topic] = payload

    EventBus.clear_subscribers()
    EventBus.subscribe(_collector)

    EventBus.publish("node.completed", {"node_id": "n1", "success": True})

    assert "node.completed" in received
    assert received["node.completed"]["node_id"] == "n1"
    assert received["node.completed"]["success"] is True
