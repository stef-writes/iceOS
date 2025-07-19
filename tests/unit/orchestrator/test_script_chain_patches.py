from typing import Any, Dict, List

import pytest

from ice_orchestrator.workflow import ScriptChain
from ice_sdk.models.node_models import NodeExecutionResult, SkillNodeConfig
from ice_sdk.orchestrator.base_workflow import FailurePolicy
from ice_sdk.skills import SkillBase, ToolContext, function_tool

# ---------------------------------------------------------------------------
# Helper tools ---------------------------------------------------------------
# ---------------------------------------------------------------------------


@function_tool(name_override="good_tool")
async def _good_tool(ctx: ToolContext) -> Dict[str, int]:  # type: ignore[override]
    """Returns a constant payload used to prove healthy execution."""
    return {"ok": 1}


@function_tool(name_override="bad_tool")
async def _bad_tool(ctx: ToolContext) -> None:  # type: ignore[override]
    """Raises an exception so we can verify gather exception handling."""
    raise RuntimeError("intentional failure for test")


# Cast to BaseTool so mypy/pyright are happy ---------------------------------
GOOD_TOOL: SkillBase = _good_tool  # type: ignore[assignment]
BAD_TOOL: SkillBase = _bad_tool  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_execute_level_handles_exceptions() -> None:
    """A failing tool node should not crash ScriptChain when policy=ALWAYS."""

    nodes: List[SkillNodeConfig] = [
        SkillNodeConfig(
            id="good", name="good", type="tool", tool_name="good_tool", tool_args={}
        ),
        SkillNodeConfig(
            id="bad", name="bad", type="tool", tool_name="bad_tool", tool_args={}
        ),
    ]

    chain = ScriptChain(
        nodes=nodes,  # type: ignore[arg-type]
        name="test_chain",
        tools=[GOOD_TOOL, BAD_TOOL],
        failure_policy=FailurePolicy.ALWAYS,
        persist_intermediate_outputs=False,
        use_cache=False,
    )

    result = await chain.execute()

    # Chain should report *success=False* because at least one node failed.
    assert result.success is False

    # Both node results should be present in output
    assert isinstance(result.output, dict)
    good_res: NodeExecutionResult = result.output["good"]  # type: ignore[index,assignment]
    bad_res: NodeExecutionResult = result.output["bad"]  # type: ignore[index,assignment]

    assert good_res.success is True
    assert bad_res.success is False
    assert "intentional failure" in (bad_res.error or "")


def test_resolve_nested_path_root() -> None:
    """Verify that path '.' returns the root object unchanged."""

    from ice_orchestrator.workflow import ScriptChain as _SC

    data: Dict[str, Any] = {"a": {"b": 1}}

    assert _SC._resolve_nested_path(data, ".") == data
    assert _SC._resolve_nested_path(data, "") == data
