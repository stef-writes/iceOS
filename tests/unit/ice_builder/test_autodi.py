from __future__ import annotations

import asyncio

import pytest

from ice_builder.dsl.workflow import WorkflowBuilder
from ice_core.services import ServiceLocator


@pytest.mark.asyncio
async def test_builder_to_workflow_requires_runtime() -> None:
    """Builder.to_workflow should succeed once a runtime Workflow is registered."""
    ServiceLocator.clear()

    # Simulate runtime layer initialisation (register Workflow prototype)
    from ice_orchestrator.workflow import Workflow as _WF

    ServiceLocator.register("workflow_proto", lambda: _WF)

    builder = WorkflowBuilder("auto_di_demo")
    builder.add_tool("noop", tool_name="aggregator", results=[])

    wf = builder.to_workflow()  # Should not raise RuntimeError
    assert wf.name == "auto_di_demo"

    # Execute trivial workflow (aggregator with zero items)
    result = await wf.execute()
    aggregate_out = result.output.get("noop", {})  # type: ignore[index]
    assert aggregate_out.get("total") == 0
    assert ServiceLocator.get("workflow_proto")
