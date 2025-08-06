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
registry._instances.setdefault(NodeType.TOOL, {})["listing_agent"] = ListingAgentTool(test_mode=False, upload=False)  # noqa: F401 – recursive import registers built-in tools
from ice_orchestrator.workflow import Workflow
from ice_core.models.node_models import ToolNodeConfig

from ice_tools.toolkits.ecommerce import EcommerceToolkit

# Register toolkit (offline / test-mode)
EcommerceToolkit(test_mode=False, upload=False).register()


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

    # 3. LoopTool – run listing_agent for every CSV row -------------------
    listing_loop = ToolNodeConfig(
        id="listing_loop",
        name="Listing Loop",
        type="tool",
        tool_name="loop_tool",
        tool_args={
            "items": "{{ load_csv.rows }}",  # Jinja template resolved by executor
            "tool": "listing_agent",
            "item_var": "product",
        },
        dependencies=["load_csv", "mock_server"],  # ensure rows + mock URL in context
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
    workflow = Workflow(nodes=nodes, name="Seller Assistant (LoopTool)", version="1.0")
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
    print("Executing workflow… (offline mode – no real API calls)")
    result = await workflow.execute()

    # Pretty print -------------------------------------------------------
    output = result.output or {}
    print("\n=== Aggregated results ===")
    print(json.dumps(output.get("summarize", {}), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
