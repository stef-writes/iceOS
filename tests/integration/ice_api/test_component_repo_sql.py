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
        # Provide minimal code to satisfy validation (tool_class_code)
        definition = {
            "type": "tool",
            "name": "unit_sql_repo_demo",
            "description": "Writer tool for integration test registration",
            "auto_register": True,
            "validate_only": False,
            "tool_class_code": (
                "from typing import Any, Dict\n"
                "from ice_core.base_tool import ToolBase\n\n"
                "class UnitSqlRepoDemoTool(ToolBase):\n"
                "    name: str = 'unit_sql_repo_demo'\n"
                "    description: str = 'Demo tool'\n"
                "    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:\n"
                "        return {'ok': True}\n"
            ),
        }

        r = await c.post(
            "/api/mcp/components/register", headers=headers, json=definition
        )
        assert r.status_code == 200, r.text

        # List components (stored index)
        r = await c.get("/api/mcp/components", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        stored = body.get("stored", [])
        assert any(
            item.get("type") == "tool" and item.get("name") == "unit_sql_repo_demo"
            for item in stored
        ), body
