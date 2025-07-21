from __future__ import annotations

from typing import Dict

import pytest

from ice_orchestrator.workflow import Workflow
from ice_sdk.models.node_models import (
    InputMapping,
    NodeExecutionResult,
    SkillNodeConfig,
)
from ice_sdk.skills import SkillBase, ToolContext, function_tool

# ---------------------------------------------------------------------------
# Helper tools --------------------------------------------------------------
# ---------------------------------------------------------------------------


@function_tool(name_override="producer")
async def _producer(ctx: ToolContext) -> Dict[str, int]:  # type: ignore[override]
    """Return a constant payload so downstream nodes can reference it."""
    return {"out": 42}


@function_tool(name_override="consumer")
async def _consumer(ctx: ToolContext, val: int) -> Dict[str, int]:  # type: ignore[override]
    """Echo the received *val* argument for assertion."""
    return {"echo": val}


PRODUCER: SkillBase = _producer  # type: ignore[assignment]
CONSUMER: SkillBase = _consumer  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Test ----------------------------------------------------------------------
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_args_placeholder_substitution():
    """Tool executor should replace placeholders using *ctx* built from InputMapping."""

    producer_node = SkillNodeConfig(
        id="produce",
        name="Producer",
        tool_name="producer",
        output_schema={"out": "int"},
    )

    consumer_node = SkillNodeConfig(
        id="consume",
        name="Consumer",
        tool_name="consumer",
        dependencies=["produce"],
        tool_args={"val": "{foo}"},
        input_mappings={
            "foo": InputMapping(source_node_id="produce", source_output_key="out")
        },
    )

    chain = Workflow(
        nodes=[producer_node, consumer_node],  # type: ignore[arg-type]
        tools=[PRODUCER, CONSUMER],
        name="placeholder-test-chain",
        persist_intermediate_outputs=False,
        use_cache=False,
    )

    result = await chain.execute()

    assert result.success is True
    assert isinstance(result.output, dict)

    consume_res: NodeExecutionResult = result.output["consume"]  # type: ignore[index]
    assert consume_res.success is True
    assert consume_res.output == {"echo": "42"}
