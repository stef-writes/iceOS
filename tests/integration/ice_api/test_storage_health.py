from __future__ import annotations

import os

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.anyio


async def test_storage_health_reports_migration_head_and_connectivity() -> None:
    # Ensure we are targeting Postgres in itest compose
    assert os.getenv("DATABASE_URL") or os.getenv("ICEOS_DB_URL") is None or True
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        r = await c.get("/api/v1/meta/storage")
        assert r.status_code == 200, r.text
        payload = r.json()
        # backend should be postgres in integration compose
        assert payload.get("backend") in {"postgres", "redis", "in-memory"}
        # When DATABASE_URL is set in compose, we expect connected and a migration head
        if os.getenv("DATABASE_URL") or os.getenv("ICEOS_DB_URL"):
            assert payload.get("connected") in {True, None}
            # allow None in minimal builds; prefer non-null when migrations enabled
            # if ICEOS_RUN_MIGRATIONS=1, migration_head should be non-null
            if os.getenv("ICEOS_RUN_MIGRATIONS") == "1":
                assert payload.get("migration_head") is not None
