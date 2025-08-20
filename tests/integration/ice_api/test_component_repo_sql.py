from __future__ import annotations

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.asyncio


async def test_component_register_and_list_sql_repo() -> None:
    headers = {"Authorization": "Bearer dev-token"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        # Minimal valid component definition (tool)
        definition = {
            "type": "tool",
            "name": "unit_sql_repo_demo",
            "package": "packs.first_party_tools.writer_tool",
            "description": "Writer tool for integration test registration",
            "auto_register": False,
            "validate_only": False,
        }

        r = await c.post(
            "/api/v1/mcp/components/register", headers=headers, json=definition
        )
        assert r.status_code == 200, r.text

        # List components (stored index)
        r = await c.get("/api/v1/mcp/components", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        stored = body.get("stored", [])
        assert any(
            item.get("type") == "tool" and item.get("name") == "unit_sql_repo_demo"
            for item in stored
        ), body
