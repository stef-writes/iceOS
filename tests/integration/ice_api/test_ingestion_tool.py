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

        # Ingest simple text (org/user injected via headers)
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
                            "org_id": "orgZ",
                            "user_id": "zoe",
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
                        "inputs": {
                            "query": "raspberries",
                            "scope": "kb",
                            "limit": 3,
                            "org_id": "orgZ",
                        }
                    },
                },
            },
        )
        assert r.status_code == 200
        body = r.json()["result"]
        content_items = body.get("content", [])
        assert content_items, body
        import json as _json

        txt = content_items[0].get("text", "{}")
        parsed = {}
        try:
            parsed = _json.loads(txt)
        except Exception:
            parsed = {}
        # Support both unwrapped and wrapped shapes
        rows = parsed.get("results")
        if not rows and isinstance(parsed.get("output"), dict):
            try:
                only_val = next(iter(parsed["output"].values()))
                rows = only_val.get("results") if isinstance(only_val, dict) else None
            except Exception:
                rows = None
        assert isinstance(rows, list) and rows, parsed
