from __future__ import annotations

import datetime as _dt
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Request

from ice_api.db.database_session_async import check_connection, get_session
from ice_api.db.orm_models_core import ComponentRecord
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
        if isinstance(lock, (bytes, bytearray)):
            try:
                lock_str: Optional[str] = lock.decode()
            except Exception:
                lock_str = None
        else:
            lock_str = str(lock) if lock is not None else None
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
        from typing import Any as _Any  # local alias to avoid top import churn

        idx: Dict[_Any, _Any] = await redis.hgetall("component:index")  # type: ignore[misc]
        if not idx:
            return {}
        decoded: Dict[str, str] = {}
        for k, v in idx.items():
            key = (
                k
                if isinstance(k, str)
                else (k.decode() if isinstance(k, (bytes, bytearray)) else str(k))
            )
            if isinstance(v, (bytes, bytearray)):
                try:
                    val_decoded = v.decode()
                except Exception:
                    val_decoded = None
                decoded[key] = val_decoded if val_decoded is not None else str(v)
            else:
                decoded[key] = str(v)
        return decoded


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


class SQLComponentRepository(ComponentRepository):
    """SQL-backed component repository using SQLAlchemy ORM.

    Stores components in the `components` table with primary key id=f"{type}:{name}".
    Lock values are derived deterministically from the serialized record so we do
    not need a dedicated column.
    """

    def _row_to_record_dict(self, row: ComponentRecord) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "definition": row.definition,
            "created_at": getattr(row, "created_at", None).isoformat()
            if getattr(row, "created_at", None)
            else None,
            "updated_at": getattr(row, "updated_at", None).isoformat()
            if getattr(row, "updated_at", None)
            else None,
            "version": int(row.version),
        }
        return payload

    async def get(
        self, component_type: str, name: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        comp_id = f"{component_type}:{name}"
        async for session in get_session():
            row = await session.get(ComponentRecord, comp_id)
            if row is None:
                return None, None
            payload = self._row_to_record_dict(row)
            return payload, _hash_lock(payload)
        return None, None

    async def put(
        self, component_type: str, name: str, payload: Dict[str, Any], lock: str
    ) -> None:
        comp_id = f"{component_type}:{name}"
        async for session in get_session():
            row = await session.get(ComponentRecord, comp_id)
            if row is None:
                row = ComponentRecord(
                    id=comp_id,
                    definition=payload.get("definition", {}),
                    version=int(payload.get("version", 1)),
                    org_id=None,
                )
                session.add(row)
            else:
                row.definition = payload.get("definition", row.definition)
                row.version = int(payload.get("version", row.version))
            await session.commit()

    async def set_index(self, key: str, lock: str) -> None:
        # No-op: index can be derived from rows on demand
        return None

    async def get_index(self) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        async for session in get_session():
            result = await session.execute(
                # Select minimal columns to reconstruct lock deterministically
                ComponentRecord.__table__.select()  # type: ignore[attr-defined]
            )
            rows: List[ComponentRecord] = [
                ComponentRecord(**dict(r))
                for r in result.mappings()  # type: ignore[call-arg]
            ]
            for r in rows:
                payload = self._row_to_record_dict(r)
                mapping[r.id] = _hash_lock(payload)
        return mapping


def choose_component_repo(app: Any) -> ComponentRepository:
    import os

    if os.getenv("USE_FAKE_REDIS") == "1":
        return InMemoryComponentRepository(app)
    # Prefer SQL when DATABASE_URL is configured and reachable
    if os.getenv("DATABASE_URL") or os.getenv("ICEOS_DB_URL"):
        try:
            import anyio

            async def _db_ok() -> bool:
                return await check_connection()

            if anyio.run(_db_ok):  # type: ignore[arg-type]
                return SQLComponentRepository()
        except Exception:
            pass
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
