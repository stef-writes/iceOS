"""my_chain – hello-world ScriptChain scaffold."""

from __future__ import annotations

import asyncio
from typing import Any, List

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.node_models import ToolNodeConfig
from ice_sdk.tools.base import ToolContext, function_tool

# ---------------------------------------------------------------------------
# Example inline tool -------------------------------------------------------
# ---------------------------------------------------------------------------


@function_tool(name_override="echo")
async def _echo_tool(ctx: ToolContext, text: str) -> dict[str, Any]:  # type: ignore[override]
    """Return the *text* argument as-is so we can observe flow output."""
    return {"echo": text}


echo_tool = _echo_tool  # mypy happy cast

# ---------------------------------------------------------------------------
# Node list ---------------------------------------------------------------
# ---------------------------------------------------------------------------

nodes: List[ToolNodeConfig] = [
    ToolNodeConfig(
        id="start",
        type="tool",
        name="echo_start",
        tool_name="echo",
        tool_args={"text": "hello"},
    ),
]

# ---------------------------------------------------------------------------
# Entry-point -------------------------------------------------------------
# ---------------------------------------------------------------------------


async def main() -> None:
    chain = ScriptChain(nodes=nodes, tools=[echo_tool], name="sample-chain")
    result = await chain.execute()
    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
