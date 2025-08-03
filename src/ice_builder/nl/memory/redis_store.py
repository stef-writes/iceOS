"""Redis-backed DraftStore implementation."""
from __future__ import annotations

import json
import os
from typing import Optional, Any

try:
    import redis.asyncio as redis
except ModuleNotFoundError:  # pragma: no cover – optional dependency
    redis = None  # type: ignore

from . import DraftState, DraftStore

_REDISTTL_SECONDS_DEFAULT: int = 60 * 60 * 24  # 24h


class RedisDraftStore(DraftStore):
    """Persist DraftState in Redis using JSON serialization."""

    def __init__(self, *, redis_url: str | None = None, ttl_seconds: int | None = None) -> None:
        if redis is None:
            raise RuntimeError("redis[asyncio] package not installed – cannot use RedisDraftStore")
        from typing import cast
        self._redis_url: str = cast(str, redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        self._ttl = ttl_seconds or int(os.getenv("DRAFTSTORE_TTL", str(_REDISTTL_SECONDS_DEFAULT)))
        from typing import Callable, Any, cast
        from_url_typed = cast(Callable[..., "redis.Redis"], redis.from_url)
        self._client = from_url_typed(self._redis_url, decode_responses=True)

    # ----------------------------- helpers ---------------------------------
    def _key(self, session_id: str) -> str:  # noqa: D401 – small util
        return f"draft:{session_id}"

    # ----------------------------- DraftStore ------------------------------
    async def load(self, session_id: str) -> Optional[DraftState]:  # noqa: D401 – protocol impl
        raw = await self._client.get(self._key(session_id))
        if raw is None:
            return None
        data = json.loads(raw)
        # We cannot rely on Pydantic; DraftState is dataclass – reconstruct manually
        return DraftState(**data)  # type: ignore[arg-type]

    async def save(self, session_id: str, state: DraftState) -> None:  # noqa: D401 – protocol impl
        data = json.dumps(state.__dict__, default=lambda o: o.__dict__)
        await self._client.set(self._key(session_id), data, ex=self._ttl)
