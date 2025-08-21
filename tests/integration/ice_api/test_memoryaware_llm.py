from __future__ import annotations

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.asyncio


async def test_memoryaware_llm_injection() -> None:
    headers = {"Authorization": "Bearer dev-token"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        # Initialize MCP
        r = await c.post(
            "/api/mcp/",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
        )
        assert r.status_code == 200

        # Submit a minimal memory-aware blueprint
        bp = {
            "schema_version": "1.2.0",
            "metadata": {"draft_name": "memaware_test"},
            "nodes": [
                {
                    "id": "llm1",
                    "type": "llm",
                    "model": "gpt-4o",
                    "prompt": "Echo: {{ inputs.msg }}",
                    "llm_config": {"provider": "openai", "model": "gpt-4o"},
                    "memory_aware": True,
                    "output_schema": {"text": "string"},
                }
            ],
        }
        # Create blueprint first to obtain an id
        create = await c.post(
            "/api/v1/blueprints/",
            headers={**headers, "X-Version-Lock": "__new__"},
            json=bp,
        )
        assert create.status_code == 201, create.text
        bp_id = create.json()["id"]
        # Execute via executions API with inputs
        r2 = await c.post(
            "/api/v1/executions/",
            headers=headers,
            json={
                "blueprint_id": bp_id,
                "inputs": {
                    "msg": "hello",
                    "session_id": "s1",
                    "org_id": "o1",
                    "user_id": "u1",
                },
            },
        )
        assert r2.status_code in (200, 202), r2.text
        exec_id = r2.json().get("execution_id")
        assert exec_id

        # Poll status until complete (simple loop)
        for _ in range(30):
            sr = await c.get(f"/api/v1/executions/{exec_id}", headers=headers)
            assert sr.status_code == 200
            data = sr.json()
            if data.get("status") in {"completed", "failed"}:
                break
        assert data.get("status") == "completed", data

        # Verify that the injected transcript write occurred by querying library list
        lr = await c.get(
            "/api/v1/library/assets",
            headers=headers,
            params={"org_id": "o1", "user_id": "u1", "limit": 10},
        )
        assert lr.status_code == 200, lr.text
        items = lr.json().get("items", [])
        assert any(i.get("key", "").startswith("asset:u1:chat:s1:") for i in items)
