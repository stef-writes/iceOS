from __future__ import annotations

"""Singleton async Redis client helper for iceOS API.

Usage::

    from ice_api.redis_client import get_redis
    redis = get_redis()
    await redis.set("foo", "bar")
"""

import os
from typing import Any, Awaitable, Callable, Optional, Union


class _RedisStub:  # type: ignore
    """Minimal async stub when the *redis* package is not installed.

    The real Redis client is only required in production.  Unit-tests that
    mock out persistence can rely on this lightweight replacement.
    """

    # ------------------------------------------------------------
    # Internal storage ------------------------------------------
    # ------------------------------------------------------------
    _hashes: dict[str, dict[str, str]] = {}
    _streams: dict[str, list[tuple[str, dict[str, str]]]] = {}

    async def ping(self) -> bool:  # noqa: D401 – stub method
        return True

    def __getattr__(self, name: str) -> Callable[..., Awaitable[Any]]:  # noqa: D401 – dynamic stub
        async def _dummy(*_args: Any, **_kwargs: Any) -> None:  # noqa: D401
            return None

        return _dummy

    # ------------------------------------------------------------
    # Hash helpers (minimal subset) ------------------------------
    # ------------------------------------------------------------

    async def hset(self, key: str, mapping: dict[str, str]) -> int:  # type: ignore[override]
        self._hashes.setdefault(key, {}).update(mapping)
        # Redis returns the number of fields that were added.
        return len(mapping)

    async def hget(self, key: str, field: str) -> Optional[str]:  # type: ignore[override]
        return self._hashes.get(key, {}).get(field)

    async def exists(self, key: str) -> bool:  # type: ignore[override]
        return key in self._hashes or key in self._streams

    # ------------------------------------------------------------
    # Stream helpers (very coarse – good enough for demo) --------
    # ------------------------------------------------------------

    async def xadd(self, stream: str, data: dict[str, str]) -> str:  # type: ignore[override]
        lst = self._streams.setdefault(stream, [])
        # Simplified ID generation (monotonic counter per stream)
        seq_id = f"{len(lst)}-0"
        lst.append((seq_id, data))
        return seq_id

    async def xread(
        self,
        streams: dict[str, str],
        block: int = 0,
        count: int | None = None,
    ) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:  # type: ignore[override]
        # Very naive implementation – returns *all* new entries after the
        # provided IDs (ignores *block* semantics).
        results: list[tuple[str, list[tuple[str, dict[str, str]]]]] = []
        for stream, last_id in streams.items():
            entries = []
            all_items = self._streams.get(stream, [])
            # Collect items with ID greater than last_id (string compare OK here)
            for seq_id, data in all_items:
                if seq_id > last_id:
                    entries.append((seq_id, data))
                    if count and len(entries) >= count:
                        break
            if entries:
                results.append((stream, entries))
        return results

try:
    # ``redis.asyncio`` provides the fully featured async client, including the
    # ``from_url`` helper used throughout the codebase.  Importing it under the
    # name *redis* keeps the API identical to the sync variant and avoids a
    # ``NameError`` when calling ``redis.from_url``.
    import redis.asyncio as redis  # type: ignore
    from redis.asyncio import Redis  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – optional for unit tests
    redis = None  # type: ignore  # keeps mypy happy when package missing
    Redis = _RedisStub  # type: ignore

__all__: list[str] = ["get_redis"]

# ---------------------------------------------------------------------------
# Singleton helper ----------------------------------------------------------
# ---------------------------------------------------------------------------

_redis_client: Optional[Union["Redis[Any]", _RedisStub]] = None

def get_redis() -> Union[Redis, _RedisStub]:  # – singleton, *sync* accessor
    """Return the shared :class:`redis.asyncio.Redis` client.

    The connection URL is read from the ``REDIS_URL`` environment variable and
    defaults to ``redis://localhost:6379/0`` when not set.

    The function is intentionally synchronous so call-sites can obtain the
    client without ``await`` – only individual Redis operations must be
    awaited.  This design aligns with FastAPI startup hooks that run in a sync
    context.
    """

    global _redis_client

    import sys
    use_fake = os.getenv("USE_FAKE_REDIS", "0") == "1" or "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules

    if _redis_client is None:
        if use_fake or redis is None:
            # Always create a new in-memory stub for test isolation
            _redis_client = _RedisStub()  # type: ignore[call-arg]
        else:
            _redis_client = redis.from_url(  # type: ignore[no-untyped-call]
                os.getenv("REDIS_URL", "redis://localhost:6379/0")
            )

    return _redis_client
