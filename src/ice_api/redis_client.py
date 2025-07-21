from __future__ import annotations

"""Singleton async Redis client helper for iceOS API.

Usage::

    from ice_api.redis_client import get_redis
    redis = get_redis()
    await redis.set("foo", "bar")
"""

import os
from functools import lru_cache

try:
    from redis.asyncio import Redis  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – optional for unit tests

    class _RedisStub:  # type: ignore
        async def ping(self):
            return True

        async def __getattr__(self, name):  # noqa: D401 – stub
            async def _dummy(*args, **kwargs):
                return None

            return _dummy

    Redis = _RedisStub  # type: ignore

__all__: list[str] = ["get_redis"]


@lru_cache(maxsize=1)
def get_redis() -> Redis:  # – singleton
    """Return shared :class:`redis.asyncio.Redis` instance.

    The connection URL is read from the ``REDIS_URL`` environment variable and
    defaults to ``redis://localhost:6379/0`` when not set.
    """

    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if hasattr(Redis, "from_url"):
        return Redis.from_url(url, decode_responses=True)  # type: ignore[attr-defined]
    return Redis()  # type: ignore[call-arg]
