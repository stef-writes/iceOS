from __future__ import annotations

import os
from typing import Any, Dict

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.anyio


async def test_memory_ingest_and_search_hash_embedder() -> None:
    os.environ["ICEOS_EMBEDDINGS_PROVIDER"] = "hash"
    headers = {"Authorization": "Bearer dev-token"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        # Ingest simple text via MCP ingestion_tool
        ingest_payload: Dict[str, Any] = {
            "method": "tool/ingestion_tool",
            "jsonrpc": "2.0",
            "id": "1",
            "params": {
                "name": "ingestion_tool",
                "type": "tool",
                "arguments": {
                    "inputs": {
                        "source_type": "text",
                        "source": "Paris is the capital of France.",
                        "scope": "kb",
                    }
                },
            },
        }
        r = await c.post("/api/mcp/", json=ingest_payload, headers=headers)
        assert r.status_code == 200, r.text
        # Search via memory_search_tool
        search_payload: Dict[str, Any] = {
            "method": "tool/memory_search_tool",
            "jsonrpc": "2.0",
            "id": "2",
            "params": {
                "name": "memory_search_tool",
                "type": "tool",
                "arguments": {
                    "inputs": {"query": "capital of France", "scope": "kb", "top_k": 3}
                },
            },
        }
        r2 = await c.post("/api/mcp/", json=search_payload, headers=headers)
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert isinstance(data, dict)
        # Minimal assertion: result object should be present
        assert "result" in data
