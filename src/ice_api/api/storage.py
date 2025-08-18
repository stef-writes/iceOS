from __future__ import annotations

import os
from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/meta", tags=["discovery", "health"])  # noqa: D401


class StorageHealth(BaseModel):
    """Storage subsystem health response.

    Returns
    -------
    StorageHealth
        The current storage backend and status.

    Example
    -------
    >>> StorageHealth(backend="redis", status="ready").model_dump()
    {'backend': 'redis', 'status': 'ready'}
    """

    backend: Literal["postgres", "redis", "in-memory"]
    status: Literal["ready"]
    migration_head: Optional[str] = None
    connected: Optional[bool] = None


@router.get("/storage", response_model=StorageHealth)
async def storage_health() -> StorageHealth:  # noqa: D401
    """Return storage mode and basic readiness.

    This is a forward-compatible health endpoint. Today it reports the
    effective storage backend based on environment configuration. Once a
    SQL-backed repository is introduced, this endpoint will also report
    current migration head and connection status.
    """
    db_url = os.getenv("DATABASE_URL") or os.getenv("ICEOS_DB_URL")
    migration_head: Optional[str] = None
    connected: Optional[bool] = None
    if db_url:
        backend: Literal["postgres", "redis", "in-memory"] = "postgres"
        try:
            # Lazy import to avoid optional dependency at startup when DB is unset
            from ice_api.db.database_session_async import (
                check_connection,  # type: ignore
            )
        except Exception:
            connected = None
        else:
            connected = await check_connection()
        # In a follow-up, wire the current Alembic head here
        migration_head = os.getenv("ALEMBIC_HEAD")
    elif os.getenv("REDIS_URL"):
        backend = "redis"
    else:
        backend = "in-memory"

    return StorageHealth(
        backend=backend,
        status="ready",
        migration_head=migration_head,
        connected=connected,
    )
