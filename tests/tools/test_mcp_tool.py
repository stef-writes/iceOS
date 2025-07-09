from __future__ import annotations

import os
from typing import Any

import pytest  # type: ignore

try:
    import respx  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – optional dependency
    pytest.skip("respx not installed", allow_module_level=True)

from ice_sdk.tools.mcp_tool import MCPTool


@pytest.mark.contract
@pytest.mark.asyncio
async def test_mcp_tool_preset_devin() -> None:
    """MCPTool should successfully call Devin MCP endpoint and parse result."""

    # Prepare -----------------------------------------------------------------
    os.environ["DEVIN_API_KEY"] = "test-devin-key"
    dummy_payload: dict[str, Any] = {"topics": ["Intro", "Setup"]}

    with respx.mock(base_url="https://mcp.devin.ai") as mock:
        mock.post("/mcp").respond(200, json=dummy_payload)

        tool = MCPTool()
        result = await tool.run(
            action="read_wiki_structure",
            repository="octocat/Hello-World",
            server="devin",
        )

        assert result["status"] == "success"
        assert result["result"] == dummy_payload
