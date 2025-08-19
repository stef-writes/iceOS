from __future__ import annotations

import asyncio
import hashlib
from typing import Any, Dict

import anyio
import pytest

from ice_api.db.database_session_async import get_session
from ice_api.db.orm_models_core import TokenRecord


@pytest.mark.anyio
async def test_db_token_resolves_identity_and_scopes_requests() -> None:
    # Insert a token record directly into DB
    raw_token = "itest-token-abc"
    th = hashlib.sha256(raw_token.encode()).hexdigest()
    async for session in get_session():
        await session.merge(
            TokenRecord(
                token_hash=th,
                org_id="orgT",
                user_id="userT",
                scopes=["memory:write", "memory:search"],
                revoked=False,
            )
        )
        await session.commit()

    import httpx

    from ice_api.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as c:
        # Use the MCP ingestion tool to write memory under token identity
        payload: Dict[str, Any] = {
            "method": "tool/memory_write_tool",
            "jsonrpc": "2.0",
            "id": "1",
            "params": {
                "name": "memory_write_tool",
                "type": "tool",
                "arguments": {"inputs": {"content": "Hello token world"}},
            },
        }
        r = await c.post(
            "/api/v1/mcp/",
            json=payload,
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert r.status_code == 200, r.text

        # Search should succeed and results should be present
        search_payload: Dict[str, Any] = {
            "method": "tool/memory_search_tool",
            "jsonrpc": "2.0",
            "id": "2",
            "params": {
                "name": "memory_search_tool",
                "type": "tool",
                "arguments": {"inputs": {"query": "token"}},
            },
        }
        r2 = await c.post(
            "/api/v1/mcp/",
            json=search_payload,
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert "result" in data
