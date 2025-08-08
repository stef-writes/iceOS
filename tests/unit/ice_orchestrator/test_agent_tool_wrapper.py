from __future__ import annotations

import pytest

from ice_core.tools import AgentTool


class FakeAgent:
    """Minimal async agent stub."""

    name = "fake_agent"
    description = "Returns greeting"

    async def execute(self, inputs):  # noqa: D401 – test stub
        name = inputs.get("name", "world")
        return {"greeting": f"Hello, {name}!"}


@pytest.mark.asyncio
async def test_agent_tool_delegation():
    agent = FakeAgent()
    tool = AgentTool(agent=agent)

    out = await tool.execute(name="Ice")
    assert out == {"greeting": "Hello, Ice!"}
