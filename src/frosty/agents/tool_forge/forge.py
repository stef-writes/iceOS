"""Stub ToolForgeAgent used in integration tests."""

from __future__ import annotations

from typing import Any

from ...context import BaseAgent

__all__ = ["ToolForgeAgent"]


class ToolForgeAgent(BaseAgent):
    """Synthesises custom SDK tools (stub)."""

    name = "tool_forge"
    capabilities = ["tool_generation"]
    version = "0.1"
    description = "Creates SDK tools from user needs"

    async def run(self, _spec: Any, **_kwargs: Any):  # noqa: D401 – stub
        return {"success": True, "tool": {"name": "example_tool"}}
