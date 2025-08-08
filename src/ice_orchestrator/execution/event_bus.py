"""Simple in-memory pub-sub used during execution.

This very small implementation keeps the footprint minimal while giving us a
single place to fan-out execution events (node completed, workflow started …).
It can later be swapped for Redis Streams, Kafka, or OTLP without touching
calling code – only the internals of ``EventBus`` would change.
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol

__all__ = ["EventBus", "Subscriber"]


class Subscriber(Protocol):
    """Callback signature expected by :pyclass:`EventBus`."""

    def __call__(self, topic: str, payload: Dict[str, Any]) -> None:  # noqa: D401
        ...


class EventBus:
    """Very small synchronous event bus.

    1. **Synchronous**: Callbacks run in the publisher's thread – good enough
       for unit tests and local dev; a real async/queue implementation can come
       later.
    2. **In-memory**: Keeps global list of subscribers; process-wide only.
    3. **Thread-safe enough**: Append/pop operations on Python lists are atomic;
       if we ever need full concurrency guarantees we can wrap with a Lock.
    """

    _subscribers: List[Subscriber] = []

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    @classmethod
    def publish(cls, topic: str, payload: Dict[str, Any]) -> None:
        """Publish *payload* to *topic*.

        For now we make a **best-effort** delivery – exceptions in a subscriber
        are caught and logged but do not stop publication to other listeners.
        """
        for cb in list(cls._subscribers):
            try:
                cb(topic, payload)
            except Exception as exc:  # pragma: no cover – defensive
                # Use lazy import to avoid circular logging dependency
                import logging

                logging.getLogger(__name__).warning(
                    "EventBus subscriber %r raised %s: %s", cb, type(exc).__name__, exc
                )

    @classmethod
    def subscribe(cls, callback: Subscriber) -> None:
        """Register *callback* to receive events."""
        cls._subscribers.append(callback)

    @classmethod
    def clear_subscribers(cls) -> None:
        """Remove all subscribers – test helper."""
        cls._subscribers.clear()
