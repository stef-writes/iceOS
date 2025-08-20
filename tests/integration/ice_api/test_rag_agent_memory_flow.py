from __future__ import annotations

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.asyncio


async def test_rag_like_flow_with_memory_tools() -> None:
    headers = {"Authorization": "Bearer dev-token"}
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

        # Write domain facts
        for key, content in [
            ("doc.capital.paris", "Paris is the capital of France."),
            ("doc.fruit.banana", "Bananas are yellow fruits."),
        ]:
            r = await c.post(
                "/api/mcp/",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "tool:memory_write_tool",
                        "arguments": {
                            "inputs": {
                                "key": key,
                                "content": content,
                                "scope": "kb",
                                "org_id": "o1",
                                "user_id": "u1",
                            }
                        },
                    },
                },
            )
            assert r.status_code == 200

        # Query semantically – emulate RAG retrieval step
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
                            "query": "france capital",
                            "scope": "kb",
                            "org_id": "o1",
                            "limit": 3,
                        }
                    },
                },
            },
        )
        assert r.status_code == 200
        result = r.json()["result"]
        content_items = result.get("content", [])
        text_blob = content_items[0].get("text", "{}") if content_items else "{}"
        import json as _json

        try:
            parsed = _json.loads(text_blob)
        except Exception:
            parsed = {}
        rows = parsed.get("results")
        if not rows and isinstance(parsed.get("output"), dict):
            try:
                only_val = next(iter(parsed["output"].values()))
                rows = only_val.get("results") if isinstance(only_val, dict) else None
            except Exception:
                rows = None
        assert rows and any(r.get("key") == "doc.capital.paris" for r in rows), parsed
