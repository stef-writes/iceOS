from __future__ import annotations

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.asyncio


async def _mcp(
    client: httpx.AsyncClient, headers: dict, method: str, params: dict
) -> dict:
    r = await client.post(
        "/api/mcp",
        headers=headers,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    assert r.status_code == 200, r.text
    return r.json()["result"]


async def test_memory_rbac_cross_org_isolation() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        # Org A identity writes a doc
        hdr_a = {
            "Authorization": "Bearer dev-token",
            "X-Org-Id": "orgA",
            "X-User-Id": "alice",
        }
        await _mcp(c, hdr_a, "initialize", {})
        await _mcp(
            c,
            hdr_a,
            "tools/call",
            {
                "name": "tool:memory_write_tool",
                "arguments": {
                    "inputs": {"key": "k1", "content": "alpha beta", "scope": "kb"}
                },
            },
        )

        # Org B identity cannot see it
        hdr_b = {
            "Authorization": "Bearer dev-token",
            "X-Org-Id": "orgB",
            "X-User-Id": "bob",
        }
        await _mcp(c, hdr_b, "initialize", {})
        res = await _mcp(
            c,
            hdr_b,
            "tools/call",
            {
                "name": "tool:memory_search_tool",
                "arguments": {"inputs": {"query": "alpha", "scope": "kb", "limit": 5}},
            },
        )
        content_items = res.get("content", [])
        txt = content_items[0].get("text", "{}") if content_items else "{}"
        assert "k1" not in txt
