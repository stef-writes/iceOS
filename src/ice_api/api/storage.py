from __future__ import annotations

import os
from typing import Literal

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


@router.get("/storage", response_model=StorageHealth)
async def storage_health() -> StorageHealth:  # noqa: D401
    """Return storage mode and basic readiness.

    This is a forward-compatible health endpoint. Today it reports the
    effective storage backend based on environment configuration. Once a
    SQL-backed repository is introduced, this endpoint will also report
    current migration head and connection status.
    """
    db_url = os.getenv("DATABASE_URL") or os.getenv("ICEOS_DB_URL")
    if db_url:
        backend: Literal["postgres", "redis", "in-memory"] = "postgres"
    elif os.getenv("REDIS_URL"):
        backend = "redis"
    else:
        backend = "in-memory"

    return StorageHealth(backend=backend, status="ready")
