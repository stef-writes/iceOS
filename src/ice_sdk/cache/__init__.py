from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from typing import Any, Optional

__all__ = [
    "LRUCache",
    "global_cache",
]


class LRUCache:
    """Simple, thread-safe in-memory LRU cache.

    This is intentionally lightweight – suitable for unit tests and
    single-process demos. In production you'd likely swap in Redis or Memcached.
    """

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
            # Move to the end to mark as recently used
            value = self._store.pop(key)
            self._store[key] = value
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._store.pop(key)
            self._store[key] = value
            # Evict least-recently-used if over capacity
            if len(self._store) > self.capacity:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# Shared tiny cache instance --------------------------------------------------
# -----------------------------------------------------------------------------

_global_cache: Optional[LRUCache] = None


def global_cache() -> LRUCache:
    """Return the singleton in-memory cache instance."""
    global _global_cache  # pylint: disable=global-statement
    if _global_cache is None:
        _global_cache = LRUCache(capacity=512)
    return _global_cache
