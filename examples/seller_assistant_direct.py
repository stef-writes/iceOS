"""Direct workflow creation example - shows what's actually failing."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

# Load env vars from .env then fallback file for demo secrets
load_dotenv()
fallback_env = Path("config/dev.env.example")
if fallback_env.is_file():
    load_dotenv(dotenv_path=fallback_env)

from ice_core.models.enums import NodeType
from ice_core.models.node_models import ToolNodeConfig

# Ensure tools are loaded and register e-commerce toolkit
from ice_core.unified_registry import registry
from ice_orchestrator.workflow import Workflow
from ice_tools.toolkits.ecommerce.listing_agent import ListingAgentTool

# Import orchestrator to register executors


# Ensure real listing_agent (test_mode False) overwrites default
registry._instances.setdefault(NodeType.TOOL, {})["listing_agent"] = ListingAgentTool(
    test_mode=False, upload=False
)
from ice_tools.toolkits.ecommerce import EcommerceToolkit

# Register a toolkit instance with default config (offline)
EcommerceToolkit(test_mode=False, upload=False).register()


async def main():
    """Create and run a minimal workflow to expose the actual errors."""

    print("Creating nodes...")

    # Create nodes with all fields
    csv_path = Path(
        "src/ice_tools/toolkits/ecommerce/Supply Yard - Overflow Items - Sheet1.csv"
    ).resolve()

    load_csv = ToolNodeConfig(
        id="load_csv",
        name="Load CSV",
        type="tool",
        tool_name="csv_loader",
        tool_args={"path": str(csv_path), "delimiter": ","},
        dependencies=[],
    )

    # Start a mock HTTP bin server for posting demo payloads
    mock_server = ToolNodeConfig(
        id="mock_server",
        name="Start Mock Server",
        type="tool",
        tool_name="mock_http_bin",
        tool_args={},
        dependencies=[],
    )

    # Listing agent first so we can reference its output
    listing_agent = ToolNodeConfig(
        id="listing_agent",
        name="Create Listing",
        type="tool",
        tool_name="listing_agent",
        tool_args={"item": "{{ item }}"},  # Explicit mapping
        dependencies=[],  # No deps - executed sequentially in loop
    )

    # Format payload for Facebook Marketplace
    fb_format = ToolNodeConfig(
        id="fb_format",
        name="Format FB Payload",
        type="tool",
        tool_name="facebook_formatter",
        tool_args={},  # Context-aware - will find listing_agent output
        dependencies=[],  # No deps - executed sequentially after listing_agent
    )

    # POST payload to mock server
    post_item = ToolNodeConfig(
        id="post_item",
        name="Post Item",
        type="tool",
        tool_name="api_poster",
        tool_args={},  # Context-aware - will find url and payload
        dependencies=[],  # No deps - mock_server context comes from parent
    )

    # Use proper LoopNodeConfig instead of LoopTool

    # Create the listing_agent node for the loop body
    listing_agent_node = ToolNodeConfig(
        id="listing_agent_inner",
        name="Create Listing",
        type="tool",
        tool_name="listing_agent",
        tool_args={"item": "{{ item }}"},  # Use loop variable
        dependencies=[],
    )

    # Create the loop node with proper body
    loop_node = LoopNodeConfig(
        id="listing_loop",
        name="Listing Loop",
        type="loop",
        items_source="load_csv.rows",  # Source of items to iterate
        item_var="item",  # Variable name for current item
        body=[listing_agent_node],  # Nodes to execute for each item
        max_iterations=100,  # Safety limit
        dependencies=["load_csv"],
    )

    summarize = ToolNodeConfig(
        id="summarize",
        name="Summarize Results",
        type="tool",
        tool_name="aggregator",
        tool_args={},
        dependencies=["listing_loop"],
    )

    nodes = [load_csv, mock_server, loop_node, summarize]

    print(f"Created {len(nodes)} nodes")

    # Create workflow
    print("\nCreating workflow...")
    wf = Workflow(nodes=nodes, name="Seller Assistant Direct", version="1.0")

    print(f"Workflow has {len(wf.nodes)} nodes")

    # Try to validate
    print("\nValidating workflow...")
    try:
        wf.validate()
        print("✅ Validation passed!")
    except Exception as e:
        print(f"❌ Validation failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return

    # Try to execute
    print("\nExecuting workflow...")
    try:
        result = await wf.execute()
        print("✅ Execution completed!")

        # Print result
        if hasattr(result, "output"):
            print(f"\nFinal output: {json.dumps(result.output, indent=2)}")
        else:
            print(f"\nResult: {result}")

    except Exception as e:
        print(f"❌ Execution failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return

    # ------------------------------------------------------------------
    # Persist mock postings for inspection ------------------------------
    # ------------------------------------------------------------------
    try:
        mock_url = result.output["mock_server"]["url"]  # type: ignore[index]
        import json as _json

        import httpx

        postings = httpx.get(mock_url, timeout=5).json()

        out_dir = Path(__file__).parent / "output"
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / "listings_direct.json"
        out_file.write_text(_json.dumps(postings, indent=2))
        # Also save original CSV rows for comparison
        rows_file = out_dir / "input_rows.json"
        rows_file.write_text(_json.dumps(result.output["load_csv"]["rows"], indent=2))  # type: ignore[index]
        print(f"\n📄 Mock postings written to {out_file.relative_to(Path.cwd())}")
        print(f"📄 Input rows written to {rows_file.relative_to(Path.cwd())}")
        print(f"🔗 Browse live at {mock_url}")
    except Exception as e:
        print(f"(Could not fetch/write mock postings: {e})")


if __name__ == "__main__":
    asyncio.run(main())
