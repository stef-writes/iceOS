from __future__ import annotations

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.asyncio


async def test_ingest_and_search() -> None:
    headers = {
        "Authorization": "Bearer dev-token",
        "X-Org-Id": "orgZ",
        "X-User-Id": "zoe",
    }
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        # Init MCP
        r = await c.post(
            "/api/mcp/",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
        )
        assert r.status_code == 200

        # Ingest simple text
        r = await c.post(
            "/api/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "tool:ingestion_tool",
                    "arguments": {
                        "inputs": {
                            "source_type": "text",
                            "source": "raspberries are red",
                            "scope": "kb",
                        }
                    },
                },
            },
        )
        assert r.status_code == 200

        # Search for it
        r = await c.post(
            "/api/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "tool:memory_search_tool",
                    "arguments": {
                        "inputs": {"query": "raspberries", "scope": "kb", "limit": 3}
                    },
                },
            },
        )
        assert r.status_code == 200
        body = r.json()["result"]
        content_items = body.get("content", [])
        assert content_items, body
        txt = content_items[0].get("text", "{}")
        assert "raspberries" in txt
