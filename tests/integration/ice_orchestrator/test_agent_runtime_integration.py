from __future__ import annotations

import asyncio
from typing import Any, Dict

from ice_orchestrator.services.agent_runtime import AgentRuntime


class _PlanAgent:
    def allowed_tools(self) -> list[str]:
        return ["writer_tool"]

    async def think(self, context: Dict[str, Any]) -> str:
        return "plan"

    def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "tool": "writer_tool",
            "inputs": {"notes": "ok", "style": "concise"},
            "done": True,
        }


def test_agent_runtime_executes_allowed_tool() -> None:
    async def _run() -> Dict[str, Any]:
        rt = AgentRuntime()
        return await rt.run(_PlanAgent(), context={})

    out = asyncio.run(_run())
    assert out.get("last_tool") == "writer_tool"
