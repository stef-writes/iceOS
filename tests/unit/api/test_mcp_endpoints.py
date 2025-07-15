"""MCP endpoint smoke‐tests (async).

These tests use FastAPI's TestClient with *lifespan* so they exercise the real
application stack (in‐memory stores).
"""

import asyncio
from typing import Any

import pytest
from httpx import AsyncClient

from ice_api.main import app

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_roundtrip() -> None:  # noqa: D401
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Register blueprint ------------------------------------------------
        blueprint_payload: dict[str, Any] = {
            "nodes": [
                {
                    "id": "sleep1",
                    "type": "tool",
                    "tool_name": "sleep",
                    "tool_args": {"seconds": 0},
                }
            ]
        }
        bp_resp = await client.post("/api/v1/mcp/blueprints", json=blueprint_payload)
        assert bp_resp.status_code == 201
        bp_id = bp_resp.json()["blueprint_id"]

        # 2. Start run -----------------------------------------------------------
        run_resp = await client.post("/api/v1/mcp/runs", json={"blueprint_id": bp_id})
        assert run_resp.status_code == 202
        run_id = run_resp.json()["run_id"]

        # 3. Poll result ----------------------------------------------------------
        for _ in range(10):
            res_resp = await client.get(f"/api/v1/mcp/runs/{run_id}")
            if res_resp.status_code == 202:
                await asyncio.sleep(0.1)
                continue
            break
        assert res_resp.status_code == 200
        data = res_resp.json()
        assert data["success"] is True
        assert data["run_id"] == run_id
