from __future__ import annotations

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.asyncio


async def _mcp(c: httpx.AsyncClient, headers: dict, method: str, params: dict) -> dict:
    r = await c.post(
        "/api/mcp/",
        headers=headers,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    assert r.status_code == 200, r.text
    return r.json()["result"]


async def test_long_horizon_memory_continuity() -> None:
    headers = {
        "Authorization": "Bearer dev-token",
        "X-Org-Id": "orgL",
        "X-User-Id": "lucy",
    }
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        await _mcp(c, headers, "initialize", {})

        # Ingest 10 facts over several steps
        facts = [f"fact {i} about cities and colors" for i in range(10)]
        for f in facts:
            await _mcp(
                c,
                headers,
                "tools/call",
                {
                    "name": "tool:ingestion_tool",
                    "arguments": {
                        "inputs": {"source_type": "text", "source": f, "scope": "kb"}
                    },
                },
            )

        # Query continuity a few times
        hits = 0
        trials = 10
        for _ in range(trials):
            res = await _mcp(
                c,
                headers,
                "tools/call",
                {
                    "name": "tool:memory_search_tool",
                    "arguments": {
                        "inputs": {"query": "cities colors", "scope": "kb", "limit": 3}
                    },
                },
            )
            content_items = res.get("content", [])
            text_blob = content_items[0].get("text", "{}") if content_items else "{}"
            if "fact" in text_blob:
                hits += 1

        # Require high recall rate (deterministic hash embedder)
        assert hits >= int(0.8 * trials)
