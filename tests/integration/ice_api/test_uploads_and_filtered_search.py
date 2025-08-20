from __future__ import annotations

import json
from typing import Any, Dict

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.anyio


async def test_uploads_and_filtered_search() -> None:
    transport = httpx.ASGITransport(app=app)
    headers = {"Authorization": "Bearer dev-token"}
    # Prepare two small documents
    file1 = (
        "resume.txt",
        b"Experienced Python developer with vector search skills",
        "text/plain",
    )
    file2 = (
        "edu.txt",
        b"Completed CS degree with focus on databases and systems",
        "text/plain",
    )
    meta = {"category": "resume", "tags": ["python", "vector"]}
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        # Upload files
        resp = await c.post(
            "/api/v1/uploads/files",
            headers=headers,
            data={
                "scope": "portfolio",
                "metadata_json": json.dumps(meta),
            },
            files=[("files", file1), ("files", file2)],
        )
        assert resp.status_code == 201, resp.text
        obj = resp.json()
        assert obj.get("count") == 2

        # Search via memory_search_tool with category filter
        payload: Dict[str, Any] = {
            "method": "tool/memory_search_tool",
            "jsonrpc": "2.0",
            "id": "1",
            "params": {
                "name": "memory_search_tool",
                "type": "tool",
                "arguments": {
                    "inputs": {
                        "query": "python",
                        "scope": "portfolio",
                        "category": "resume",
                        "top_k": 3,
                    }
                },
            },
        }
        r2 = await c.post("/api/mcp/", json=payload, headers=headers)
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert "result" in data
