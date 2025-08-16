from __future__ import annotations

import asyncio
from typing import Any, Dict

from ice_core.unified_registry import register_tool_factory
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
        # Ensure writer_tool is registered for this process
        register_tool_factory(
            "writer_tool", "packs.first_party_tools.writer_tool:create_writer_tool"
        )
        rt = AgentRuntime()
        return await rt.run(_PlanAgent(), context={})

    out = asyncio.run(_run())
    assert out.get("last_tool") == "writer_tool"
