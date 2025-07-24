from __future__ import annotations

# ruff: noqa: E402

"""Lightweight in-memory cache for core-level consumers.

This file restores the original *ice_core.cache* public surface relied upon by
`ice_orchestrator.workflow.Workflow`.  The implementation is identical to the
version now living in *ice_sdk.cache* but duplicated here to avoid upward
imports across layer boundaries (Rule 12).
"""

from collections import OrderedDict
from threading import Lock
from typing import Any, Optional

__all__: list[str] = ["LRUCache", "global_cache"]

class LRUCache:  # – simple helper
    """Thread-safe LRU cache suitable for unit tests and single-process runs."""

    def __init__(self, capacity: int = 256):
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        self.capacity = capacity
        self._store: "OrderedDict[str, Any]" = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                return None
            value = self._store.pop(key)
            self._store[key] = value  # mark as recently used
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._store.pop(key)
            self._store[key] = value
            if len(self._store) > self.capacity:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

# Singleton instance ---------------------------------------------------------

_global_cache: Optional[LRUCache] = None

def global_cache() -> LRUCache:
    """Return process-wide shared LRU cache instance."""

    global _global_cache  # pylint: disable=global-statement
    if _global_cache is None:
        _global_cache = LRUCache(capacity=512)
    return _global_cache
