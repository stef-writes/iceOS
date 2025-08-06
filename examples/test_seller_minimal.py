"""Minimal seller assistant test."""

import asyncio
from pathlib import Path
from ice_core.models.node_models import ToolNodeConfig, LoopNodeConfig
from ice_orchestrator.workflow import Workflow
import ice_orchestrator  # Register executors
import ice_tools
from ice_tools.toolkits.ecommerce import EcommerceToolkit

# Register toolkit
EcommerceToolkit(test_mode=True, upload=False).register()

async def main():
    # CSV loader
    csv_path = Path("src/ice_tools/toolkits/ecommerce/Supply Yard - Overflow Items - Sheet1.csv").resolve()
    load_csv = ToolNodeConfig(
        id="load_csv",
        name="Load CSV",
        type="tool",
        tool_name="csv_loader",
        tool_args={"path": str(csv_path), "delimiter": ","},
        dependencies=[]
    )
    
    # Listing agent - context-aware, will find 'item' from loop
    listing_agent = ToolNodeConfig(
        id="listing_agent",
        name="Create Listing",
        type="tool",
        tool_name="listing_agent",
        tool_args={},
        dependencies=[]
    )
    
    # Loop
    process_loop = LoopNodeConfig(
        id="process_loop",
        name="Process Items",
        type="loop",
        items_source="load_csv.rows",
        item_var="item",
        body=[listing_agent],  # Just one tool in the loop
        dependencies=["load_csv"]
    )
    
    # Aggregator - context-aware, will find process_loop results
    aggregator = ToolNodeConfig(
        id="aggregate",
        name="Aggregate Results",
        type="tool",
        tool_name="aggregator",
        tool_args={},
        dependencies=["process_loop"]
    )
    
    # Create workflow
    wf = Workflow(
        nodes=[load_csv, process_loop, aggregator],
        name="Minimal Seller"
    )
    
    print("Executing workflow...")
    result = await wf.execute()
    
    if hasattr(result, 'output'):
        output = result.output
        print(f"\nCSV rows: {len(output.get('load_csv', {}).get('rows', []))}")
        
        # Check loop result in detail
        loop_result = output.get('process_loop', {})
        print(f"\nLoop result: {loop_result}")
        
        if isinstance(loop_result, dict) and 'error' in loop_result:
            print(f"Loop error: {loop_result['error']}")
        
        print(f"\nAggregator: {output.get('aggregate', {})}")

if __name__ == "__main__":
    asyncio.run(main())