"""Seller Assistant - Fluent API demo using LoopTool

This version avoids the fragile LoopNode by using the context-aware `loop_tool`
which simply runs `listing_agent` for every CSV row and returns the list of
results.  The orchestrator still sees one node, so we keep the “each node runs
exactly once” contract while getting reliable batched execution.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment ----------------------------------------------------------------
# ---------------------------------------------------------------------------

load_dotenv()
fallback_env = Path("config/dev.env.example")
if fallback_env.is_file():
    load_dotenv(dotenv_path=fallback_env)

# ---------------------------------------------------------------------------
# iceOS imports --------------------------------------------------------------
# ---------------------------------------------------------------------------

import ice_orchestrator  # noqa: F401 – registers executors
import ice_tools
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType
from ice_tools.toolkits.ecommerce.listing_agent import ListingAgentTool
registry._instances.setdefault(NodeType.TOOL, {})["listing_agent"] = ListingAgentTool(test_mode=False, upload=True)  # noqa: F401 – recursive import registers built-in tools
from ice_orchestrator.workflow import Workflow
from ice_core.models.node_models import ToolNodeConfig

from ice_tools.toolkits.ecommerce import EcommerceToolkit

# Register toolkit (offline / test-mode)
EcommerceToolkit(test_mode=False, upload=True).register()


# ---------------------------------------------------------------------------
# Workflow builder -----------------------------------------------------------
# ---------------------------------------------------------------------------

CSV_PATH_DEFAULT = Path(
    "src/ice_tools/toolkits/ecommerce/"
    "Supply Yard - Overflow Items - Sheet1.csv"
).resolve()


def build_seller_workflow(csv_path: Path | None = None) -> Workflow:  # noqa: D401
    """Build the seller assistant workflow using LoopTool."""

    csv_path = csv_path or CSV_PATH_DEFAULT

    # 1. Load CSV rows ----------------------------------------------------
    load_csv = ToolNodeConfig(
        id="load_csv",
        name="Load Product CSV",
        type="tool",
        tool_name="csv_loader",
        tool_args={"path": str(csv_path), "delimiter": ","},
    )

    # 2. Mock HTTP bin server (used by listing_agent -> marketplace_client)
    mock_server = ToolNodeConfig(
        id="mock_server",
        name="Start Mock Server",
        type="tool",
        tool_name="mock_http_bin",
    )

    # 3. LoopNode – run listing_agent for every CSV row -------------------
    from ice_core.models.node_models import LoopNodeConfig
    
    # Create the listing_agent node for the loop body
    listing_agent_node = ToolNodeConfig(
        id="listing_agent_inner",
        name="Create Listing",
        type="tool",
        tool_name="listing_agent",
        tool_args={"item": "{{ item }}"},  # Use loop variable
        dependencies=[]
    )
    
    # Create the loop node with proper body
    listing_loop = LoopNodeConfig(
        id="listing_loop",
        name="Listing Loop",
        type="loop",
        items_source="load_csv.rows",  # Source of items to iterate
        item_var="item",  # Variable name for current item
        body=[listing_agent_node],  # Nodes to execute for each item
        max_iterations=100,  # Safety limit
        dependencies=["load_csv", "mock_server"]
    )

    # 4. Aggregator – summarise loop results ------------------------------
    summarize = ToolNodeConfig(
        id="summarize",
        name="Summarize Results",
        type="tool",
        tool_name="aggregator",
        tool_args={},  # context-aware – finds listing_loop output
        dependencies=["listing_loop"],
    )

    # Assemble workflow ----------------------------------------------------
    nodes = [load_csv, mock_server, listing_loop, summarize]
    workflow = Workflow(nodes=nodes, name="Seller Assistant (LoopNode)", version="1.0")
    return workflow


# ---------------------------------------------------------------------------
# Main entry-point -----------------------------------------------------------
# ---------------------------------------------------------------------------

async def main() -> None:  # pragma: no cover – demo script
    workflow = build_seller_workflow()

    # Validate -----------------------------------------------------------
    print("Validating workflow…")
    workflow.validate()
    print("✅ Validation passed!\n")

    # Execute ------------------------------------------------------------
    print("Executing workflow… (production mode – real API calls)")
    result = await workflow.execute()

    # Pretty print -------------------------------------------------------
    output = result.output or {}
    print("\n=== Aggregated results ===")
    print(json.dumps(output.get("summarize", {}), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
