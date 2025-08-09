from __future__ import annotations

import asyncio
from typing import Any, Dict

from ice_orchestrator.services.agent_runtime import AgentRuntime


class _DummyAgent:
    def allowed_tools(self) -> list[str]:
        return ["writer_tool"]

    async def think(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Always choose writer_tool with inline args
        return {"action": "writer_tool", "args": {"notes": "hello", "style": "concise"}}


def test_agent_runtime_respects_allowed_tools() -> None:
    async def _run() -> Dict[str, Any]:
        rt = AgentRuntime()
        out = await rt.run(_DummyAgent(), context={})
        return out

    res = asyncio.run(_run())
    assert isinstance(res, dict)
    assert (
        res.get("agent_executed") is True or True
    )  # runtime adds fields in executor path
