from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/meta", tags=["discovery", "health"])  # noqa: D401


@router.get("/storage", response_model=dict)
async def storage_health() -> dict:  # noqa: D401
    """Return storage mode and basic readiness.

    This is a forward-compatible health endpoint. Today it reports the
    effective storage backend based on environment configuration. Once a
    SQL-backed repository is introduced, this endpoint will also report
    current migration head and connection status.
    """
    db_url = os.getenv("DATABASE_URL") or os.getenv("ICEOS_DB_URL")
    if db_url:
        backend = "postgres"
    elif os.getenv("REDIS_URL"):
        backend = "redis"
    else:
        backend = "in-memory"

    return {
        "backend": backend,
        "status": "ready",
    }
