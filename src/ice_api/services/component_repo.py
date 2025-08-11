from __future__ import annotations

import datetime as _dt
import hashlib
import json
from typing import Any, Dict, Optional, Tuple

from fastapi import Request

from ice_api.redis_client import get_redis


def _hash_lock(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class ComponentRepository:
    async def get(
        self, component_type: str, name: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        raise NotImplementedError

    async def put(
        self, component_type: str, name: str, payload: Dict[str, Any], lock: str
    ) -> None:
        raise NotImplementedError

    async def set_index(self, key: str, lock: str) -> None:
        raise NotImplementedError

    async def get_index(self) -> Dict[str, str]:
        raise NotImplementedError


class RedisComponentRepository(ComponentRepository):
    async def get(
        self, component_type: str, name: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        redis = get_redis()
        raw = await redis.hget(f"component:{component_type}:{name}", "json")  # type: ignore[misc]
        if not raw:
            return None, None
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode()
        data = json.loads(raw)
        lock = await redis.hget(f"component:{component_type}:{name}", "lock")  # type: ignore[misc]
        lock_str = (
            lock.decode()
            if isinstance(lock, (bytes, bytearray))
            else (str(lock) if lock else None)
        )
        return data, lock_str

    async def put(
        self, component_type: str, name: str, payload: Dict[str, Any], lock: str
    ) -> None:
        redis = get_redis()
        await redis.hset(
            f"component:{component_type}:{name}",
            mapping={"json": json.dumps(payload), "lock": lock},
        )

    async def set_index(self, key: str, lock: str) -> None:
        redis = get_redis()
        await redis.hset("component:index", mapping={key: lock})

    async def get_index(self) -> Dict[str, str]:
        redis = get_redis()
        idx = await redis.hgetall("component:index")  # type: ignore[misc]
        if not idx:
            return {}
        return {
            (k.decode() if isinstance(k, (bytes, bytearray)) else str(k)): (
                v.decode() if isinstance(v, (bytes, bytearray)) else str(v)
            )
            for k, v in idx.items()
        }


class InMemoryComponentRepository(ComponentRepository):
    def __init__(self, request_or_app: Request | Any):  # type: ignore[no-redef]
        app = request_or_app if hasattr(request_or_app, "state") else request_or_app.app
        self._app = app
        if not hasattr(self._app.state, "components"):
            self._app.state.components = {}
        if not hasattr(self._app.state, "components_index"):
            self._app.state.components_index = {}

    async def get(
        self, component_type: str, name: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        store: Dict[str, Dict[str, Any]] = self._app.state.components  # type: ignore[attr-defined]
        key = f"component:{component_type}:{name}"
        rec = store.get(key)
        if not rec:
            return None, None
        lock = rec.get("lock")
        return rec.get("json"), lock

    async def put(
        self, component_type: str, name: str, payload: Dict[str, Any], lock: str
    ) -> None:
        store: Dict[str, Dict[str, Any]] = self._app.state.components  # type: ignore[attr-defined]
        key = f"component:{component_type}:{name}"
        store[key] = {
            "json": payload,
            "lock": lock,
            "updated_at": _dt.datetime.utcnow().isoformat(),
        }
        self._app.state.components = store  # type: ignore[attr-defined]

    async def set_index(self, key: str, lock: str) -> None:
        idx: Dict[str, str] = self._app.state.components_index  # type: ignore[attr-defined]
        idx[key] = lock
        self._app.state.components_index = idx  # type: ignore[attr-defined]

    async def get_index(self) -> Dict[str, str]:
        return dict(self._app.state.components_index)  # type: ignore[attr-defined]


def choose_component_repo(app: Any) -> ComponentRepository:
    import os

    if os.getenv("USE_FAKE_REDIS") == "1":
        return InMemoryComponentRepository(app)
    try:
        # verify connectivity
        redis = get_redis()
        # ping may not exist on stub
        if hasattr(redis, "ping"):
            # type: ignore[misc]
            import anyio

            async def _ping() -> None:
                await redis.ping()

            anyio.run(_ping)
        return RedisComponentRepository()
    except Exception:
        return InMemoryComponentRepository(app)
