#!/usr/bin/env python3
"""Complete MCP (Model Context Protocol) example.

This example demonstrates the full MCP workflow:
1. Create a blueprint with nodes
2. Execute the blueprint via MCP
3. Get results and handle errors

Run this example:
    python examples/mcp_complete_example.py
"""

import asyncio
import json

from ice_core.models.mcp import Blueprint, NodeSpec, RunOptions, RunRequest
from ice_sdk.protocols.mcp.client import MCPClient


async def main():
    """Demonstrate complete MCP workflow."""

    # Initialize MCP client
    client = MCPClient(base_url="http://localhost:8000")

    print("🚀 iceOS MCP Complete Example")
    print("=" * 50)

    # Step 1: Create a blueprint
    print("\n1. Creating blueprint...")

    blueprint = Blueprint(
        blueprint_id="demo_workflow",
        nodes=[
            NodeSpec(
                id="echo",
                type="tool",
                tool_name="echo",
                tool_args={"message": "Hello from iceOS MCP!"},
            ),
            NodeSpec(
                id="sum",
                type="tool",
                tool_name="sum",
                tool_args={"numbers": [1, 2, 3, 4, 5]},
            ),
        ],
        metadata={
            "description": "Simple demo workflow with echo and sum",
            "author": "iceOS Team",
        },
    )

    # Register the blueprint
    try:
        ack = await client.create_blueprint(blueprint)
        print(f"✅ Blueprint created: {ack.blueprint_id}")
        print(f"   Status: {ack.status}")
    except Exception as e:
        print(f"❌ Failed to create blueprint: {e}")
        return

    # Step 2: Execute the blueprint
    print("\n2. Executing blueprint...")

    try:
        RunRequest(blueprint_id=ack.blueprint_id, options=RunOptions(max_parallel=5))

        run_ack = await client.start_run(blueprint_id=ack.blueprint_id, max_parallel=5)

        print(f"✅ Run started: {run_ack.run_id}")
        print(f"   Status endpoint: {run_ack.status_endpoint}")
        print(f"   Events endpoint: {run_ack.events_endpoint}")

    except Exception as e:
        print(f"❌ Failed to start run: {e}")
        return

    # Step 3: Wait for results
    print("\n3. Waiting for results...")

    try:
        result = await client.await_result(run_ack.run_id, poll_interval=0.5)

        print(f"✅ Run completed: {result.run_id}")
        print(f"   Success: {result.success}")
        print(
            f"   Duration: {(result.end_time - result.start_time).total_seconds():.2f}s"
        )

        if result.error:
            print(f"   Error: {result.error}")
        else:
            print(f"   Output: {json.dumps(result.output, indent=2)}")

    except Exception as e:
        print(f"❌ Failed to get results: {e}")
        return

    # Step 4: Demonstrate inline blueprint execution
    print("\n4. Executing inline blueprint...")

    try:
        inline_blueprint = Blueprint(
            blueprint_id="inline_demo",
            nodes=[
                NodeSpec(
                    id="sleep", type="tool", tool_name="sleep", tool_args={"seconds": 1}
                ),
            ],
        )

        inline_run = await client.start_run(blueprint=inline_blueprint)
        inline_result = await client.await_result(inline_run.run_id)

        print(f"✅ Inline run completed: {inline_result.run_id}")
        print(f"   Success: {inline_result.success}")

    except Exception as e:
        print(f"❌ Failed to execute inline blueprint: {e}")

    print("\n🎉 MCP example completed successfully!")


if __name__ == "__main__":
    # Make sure the API server is running first:
    # uvicorn ice_api.main:app --reload --host 0.0.0.0 --port 8000

    print("Note: Make sure the iceOS API server is running:")
    print("  uvicorn ice_api.main:app --reload --host 0.0.0.0 --port 8000")
    print()

    asyncio.run(main())
