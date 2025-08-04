"""Direct workflow creation example - shows what's actually failing."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from ice_core.models.node_models import ToolNodeConfig, LoopNodeConfig
from ice_orchestrator.workflow import Workflow

# Ensure tools are loaded
import ice_tools


async def main():
    """Create and run a minimal workflow to expose the actual errors."""
    
    print("Creating nodes...")
    
    # Create nodes with all fields
    csv_path = Path("src/ice_tools/ecommerce/Supply Yard - Overflow Items - Sheet1.csv").resolve()
    
    load_csv = ToolNodeConfig(
        id="load_csv",
        name="Load CSV",
        type="tool",
        tool_name="csv_loader",
        tool_args={"path": str(csv_path), "delimiter": ","},
        dependencies=[]
    )
    
    process_loop = LoopNodeConfig(
        id="process_loop",
        name="Process Items",
        type="loop",
        items_source="load_csv.rows",
        item_var="item",
        body_nodes=["listing_agent"],
        dependencies=["load_csv"]
    )
    
    listing_agent = ToolNodeConfig(
        id="listing_agent",
        name="Create Listing",
        type="tool",
        tool_name="listing_agent",
        tool_args={
            "margin_percent": 25.0,
            "model": "gpt-4o",
            "test_mode": True
        },
        dependencies=[]
    )
    
    aggregator = ToolNodeConfig(
        id="aggregate",
        name="Aggregate Results",
        type="tool",
        tool_name="aggregator",
        tool_args={"results": "{{ process_loop.* }}"},
        dependencies=["process_loop"]
    )
    
    nodes = [load_csv, process_loop, listing_agent, aggregator]
    
    print(f"Created {len(nodes)} nodes")
    
    # Create workflow
    print("\nCreating workflow...")
    wf = Workflow(
        nodes=nodes,
        name="Seller Assistant Direct",
        version="1.0"
    )
    
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
        if hasattr(result, 'output'):
            print(f"\nFinal output: {json.dumps(result.output, indent=2)}")
        else:
            print(f"\nResult: {result}")
            
    except Exception as e:
        print(f"❌ Execution failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())