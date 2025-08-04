"""Integration test: run the Seller Assistant demo blueprint end-to-end in test-mode."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from ice_builder.dsl.workflow import WorkflowBuilder
from ice_core.models.node_models import ToolNodeConfig, LoopNodeConfig
from ice_orchestrator.workflow import Workflow


@pytest.mark.asyncio
async def test_seller_assistant_demo(tmp_path: Path) -> None:
    # Use the sample CSV from repo – path relative to project root
    csv_path = Path("src/ice_tools/ecommerce/Supply Yard - Overflow Items - Sheet1.csv").resolve()
    assert csv_path.is_file(), "Fixture CSV missing"

    os.environ["CSV_PATH"] = str(csv_path)
    os.environ["ICE_TEST_MODE"] = "1"
    os.environ["ICE_MARKETPLACE_ENDPOINT"] = "https://example.com/mock"
    os.environ["ICE_MARKETPLACE_API_KEY"] = "dummy"
    os.environ["ICE_CONTEXT_PERSIST"] = "0"

    # Build workflow via fluent builder ---------------------------------
    builder = WorkflowBuilder("seller_demo")
    builder.add_tool(
        "load_csv",
        tool_name="csv_loader",
        path=str(csv_path),
        delimiter=",",
    )
    builder.add_loop(
        "process_loop",
        items_source="load_csv.rows",
        body_nodes=["listing_agent"],
        item_var="item",
    )
    builder.add_tool(
        "listing_agent",
        tool_name="listing_agent",
        margin_percent=25.0,
        model="gpt-4o",
        test_mode=True,
    )
    builder.connect("load_csv", "process_loop")
    builder.connect("process_loop", "listing_agent")
    builder.add_tool(
        "aggregate",
        tool_name="aggregator",
        results="{{ process_loop.* }}",
    )
    builder.connect("process_loop", "aggregate")

    from ice_core.services import ServiceLocator
    from ice_orchestrator.workflow import Workflow as _WF
    ServiceLocator.register("workflow_proto", lambda: _WF)

    workflow: Workflow = builder.to_workflow()

    workflow.validate()
    result = await workflow.execute()
    # Extract the aggregator output – workflow returns per-node outputs
    results_dict = result.output if hasattr(result, "output") else {}
    aggregate_out = results_dict.get("aggregate", {})

    assert aggregate_out.get("total") == 9
    assert aggregate_out.get("failures") == 0
    assert aggregate_out.get("success") == 9
