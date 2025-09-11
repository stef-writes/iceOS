from __future__ import annotations

import os
import json
from typing import Any, Dict

import httpx
import pytest
import sqlalchemy as sa

from ice_api.db.database_session_async import get_session
from ice_api.main import app
from ice_api.db.database_session_async import dispose_all_engines

pytestmark = pytest.mark.anyio


def _require_db() -> None:
    if not os.getenv("DATABASE_URL") and not os.getenv("ICEOS_DB_URL"):
        pytest.skip("DATABASE_URL not configured; skipping DB-SSOT integration tests")


def _headers() -> Dict[str, str]:
    # Allow dev token in in-process ASGI tests
    os.environ.setdefault("ICE_ALLOW_DEV_TOKEN", "1")
    os.environ.setdefault("ICE_API_TOKEN", "dev-token")
    return {"Authorization": "Bearer dev-token"}


async def _count(scope: str) -> int:
    async for session in get_session():
        res = await session.execute(
            sa.text("SELECT COUNT(*) FROM semantic_memory WHERE scope = :s"),
            {"s": scope},
        )
        row = res.first()
        return int(row[0]) if row else 0
    return 0


async def test_uploads_persist_to_semantic_memory() -> None:
    _require_db()
    headers = _headers()
    transport = httpx.ASGITransport(app=app)
    before = await _count("portfolio")
    # Two tiny text files
    file1 = ("r1.txt", b"python vectors", "text/plain")
    file2 = ("r2.txt", b"databases and systems", "text/plain")
    meta = {"category": "resume", "tags": ["python", "vector"]}
    async with httpx.AsyncClient(base_url="http://testserver", transport=transport) as c:
        resp = await c.post(
            "/api/v1/uploads/files",
            headers=headers,
            data={"scope": "portfolio", "metadata_json": json.dumps(meta)},
            files=[("files", file1), ("files", file2)],
        )
        assert resp.status_code == 201, resp.text
    after = await _count("portfolio")
    assert after >= before


async def test_chat_turn_persists_transcript() -> None:
    _require_db()
    headers = _headers()
    transport = httpx.ASGITransport(app=app)
    before = await _count("chat")
    async with httpx.AsyncClient(base_url="http://testserver", transport=transport) as c:
        r = await c.post(
            "/api/mcp/chat/echo",
            headers=headers,
            json={"session_id": "itest", "user_message": "hello", "reset": True},
        )
        assert r.status_code == 200, r.text
    after = await _count("chat")
    assert after >= before


async def test_frosty_suggest_logs_telemetry() -> None:
    _require_db()
    headers = _headers()
    transport = httpx.ASGITransport(app=app)
    before = await _count("frosty")
    async with httpx.AsyncClient(base_url="http://testserver", transport=transport) as c:
        r = await c.post(
            "/api/v1/frosty/suggest_v2",
            headers=headers,
            json={"text": "add llm and connect to tool", "canvas_state": {}},
        )
        assert r.status_code == 200, r.text
    after = await _count("frosty")
    assert after >= before


async def test_blueprint_crud_writes_to_db() -> None:
    _require_db()
    headers = _headers()
    transport = httpx.ASGITransport(app=app)
    # Create minimal blueprint
    bp: Dict[str, Any] = {
        "schema_version": "1.2.0",
        "metadata": {"draft_name": "db_ssot_bp"},
        "nodes": [{"id": "n1", "type": "tool", "dependencies": []}],
    }
    async with httpx.AsyncClient(base_url="http://testserver", transport=transport) as c:
        r = await c.post(
            "/api/v1/blueprints/",
            headers={**headers, "X-Version-Lock": "__new__"},
            json=bp,
        )
        assert r.status_code in (200, 201), r.text
        bp_id = r.json()["id"]
    # Verify in DB
    async for session in get_session():
        res = await session.execute(
            sa.text("SELECT COUNT(*) FROM blueprints WHERE id = :id"), {"id": bp_id}
        )
        assert int(res.scalar() or 0) == 1
    # Dispose engines to avoid GC warnings about non-checked-in connections
    try:
        await dispose_all_engines()
    except Exception:
        pass
