from __future__ import annotations

import asyncio

import pytest

from ice_builder.dsl.workflow import WorkflowBuilder
from ice_core.services import ServiceLocator


@pytest.mark.asyncio
async def test_builder_auto_di() -> None:
    """Builder should auto-register Workflow class when absent."""
    ServiceLocator.clear()

    builder = WorkflowBuilder("auto_di_demo")
    builder.add_tool("noop", tool_name="aggregator", results=[])

    wf = builder.to_workflow()  # Should not raise KeyError
    assert wf.name == "auto_di_demo"

    # Execute trivial workflow (aggregator with zero items)
    result = await wf.execute()
    aggregate_out = result.output.get("noop", {})  # type: ignore[index]
    assert aggregate_out.get("total") == 0
    assert ServiceLocator.get("workflow_proto")  # auto-registered
