from __future__ import annotations

import asyncio
import json
import logging
import os
from threading import Thread
from typing import (
    Any,
    Awaitable,
    Dict,
    Optional,
    Protocol,
    TypeVar,
    Union,
    cast,
    runtime_checkable,
)

from .store_base import BaseContextStore

T = TypeVar("T")


@runtime_checkable
class _HashClient(Protocol):
    def hget(
        self, key: str, field: str
    ) -> Union[str, bytes, None, Awaitable[str | bytes | None]]: ...
    def hset(self, key: str, mapping: Dict[str, str]) -> Union[int, Awaitable[int]]: ...
    def hdel(self, key: str, *fields: str) -> Union[int, Awaitable[int]]: ...
    def delete(self, key: str) -> Union[int, Awaitable[int]]: ...


logger = logging.getLogger(__name__)


class RedisContextStore(BaseContextStore):
    """Redis-backed context store.

    - Keys are stored under a single Redis hash: ``context:store`` by default
      (override with CONTEXT_STORE_HASH env var).
    - Values are JSON-serialized dicts matching the file store schema.
    - Methods are sync to match current call sites.
    """

    def __init__(self, *, hash_key: Optional[str] = None) -> None:
        env_hash = os.getenv("CONTEXT_STORE_HASH")
        self.hash_key: str = (
            hash_key
            if hash_key is not None
            else (env_hash if env_hash is not None else "context:store")
        )
        # Import lazily to avoid circular deps at module import time
        from ice_api.redis_client import get_redis

        # Narrow to minimal protocol
        self._redis: _HashClient = cast(_HashClient, get_redis())

        # Ensure background loop exists for resolving awaitables from sync path
        _ensure_bg_loop()

    def get(self, node_id: str) -> Any:  # noqa: D401
        """Retrieve context data for a node."""
        try:
            raw = _resolve(self._redis.hget(self.hash_key, node_id))
            if not raw:
                return None
            if isinstance(raw, str):
                text = raw
            else:
                text = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
            data = json.loads(text)
            value = data.get("data")
            return value
        except Exception as exc:  # pragma: no cover
            logger.warning("RedisContextStore.get failed: %s", exc)
            return None

    def set(
        self,
        node_id: str,
        context: Dict[str, Any],
        schema: Optional[Dict[str, str]] = None,
    ) -> None:  # noqa: D401
        """Set context data for a node."""
        try:
            payload = json.dumps({"data": context})
            _resolve(self._redis.hset(self.hash_key, mapping={node_id: payload}))
        except Exception as exc:  # pragma: no cover
            logger.warning("RedisContextStore.set failed: %s", exc)

    def update(
        self,
        node_id: str,
        content: Any,
        execution_id: Optional[str] = None,
        schema: Optional[Dict[str, str]] = None,
    ) -> None:  # noqa: D401
        """Update context data for a node, optionally with an execution ID."""
        try:
            entry: Dict[str, Any] = {"data": content}
            if execution_id:
                entry["execution_id"] = execution_id
            payload = json.dumps(entry, default=str)
            _resolve(self._redis.hset(self.hash_key, mapping={node_id: payload}))
        except Exception as exc:  # pragma: no cover
            logger.warning("RedisContextStore.update failed: %s", exc)

    def clear(self, node_id: Optional[str] = None) -> None:  # noqa: D401
        """Clear context for a specific node or all nodes."""
        try:
            if node_id:
                _resolve(self._redis.hdel(self.hash_key, node_id))
            else:
                _resolve(self._redis.delete(self.hash_key))
        except Exception as exc:  # pragma: no cover
            logger.warning("RedisContextStore.clear failed: %s", exc)

    # -------------------- Internal sync bridge over async client --------------------


_bg_loop: asyncio.AbstractEventLoop | None = None


def _ensure_bg_loop() -> asyncio.AbstractEventLoop:
    global _bg_loop
    if _bg_loop and _bg_loop.is_running():
        return _bg_loop
    loop = asyncio.new_event_loop()

    def _run() -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    t = Thread(target=_run, name="redis-bg-loop", daemon=True)
    t.start()
    _bg_loop = loop
    return loop


def _resolve(v: Union[T, Awaitable[T]]) -> T:
    if asyncio.iscoroutine(v):
        loop = _ensure_bg_loop()
        fut = asyncio.run_coroutine_threadsafe(v, loop)
        return cast(T, fut.result())
    return cast(T, v)
