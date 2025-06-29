from __future__ import annotations

from typing import Any

from ice_sdk.tools.base import BaseTool, ToolContext


class DemoTool(BaseTool):
    """DemoTool – describe what the tool does."""

    name = "demo_tool"
    description = "Describe what the tool does"

    async def run(self, ctx: ToolContext, **kwargs: Any) -> Any:  # noqa: D401
        """Execute the tool.

        Args:
            ctx: Execution context injected by the orchestrator.
            **kwargs: Parameters defined by the agent/node.
        """
        # IMPLEMENT YOUR TOOL LOGIC HERE -----------------------------------
        return {"echo": kwargs}
