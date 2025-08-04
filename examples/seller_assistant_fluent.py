"""Seller Assistant - Fluent API Demo

This demonstrates how a user would naturally build and run an e-commerce workflow.
The system should handle all validation, error reporting, and execution automatically.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from ice_orchestrator.workflow import Workflow
from ice_core.models.node_models import ToolNodeConfig, LoopNodeConfig
from ice_core.models.enums import NodeType

# Ensure tools are loaded
import ice_tools


async def build_seller_workflow() -> Workflow:
    """Build a seller assistant workflow using the fluent API."""
    
    # Create workflow with empty nodes initially
    wf = Workflow(nodes=[], name="Seller Assistant", version="1.0")
    
    # Add CSV loader node
    csv_path = Path("src/ice_tools/ecommerce/Supply Yard - Overflow Items - Sheet1.csv").resolve()
    wf.add_node(
        ToolNodeConfig(
            id="load_csv",
            name="Load Product CSV",
            type="tool",
            tool_name="csv_loader",
            tool_args={"path": str(csv_path), "delimiter": ","}
        )
    )
    
    # Add loop to process each item
    wf.add_node(
        LoopNodeConfig(
            id="process_items",
            name="Process Each Product",
            type="loop",
            items_source="load_csv.rows",
            item_var="product",
            body_nodes=["create_listing"],
            dependencies=["load_csv"]
        )
    )
    
    # Add listing agent inside loop
    wf.add_node(
        ToolNodeConfig(
            id="create_listing",
            name="Create Marketplace Listing",
            type="tool",
            tool_name="listing_agent",
            tool_args={
                "item": "{{ product }}",
                "margin_percent": 25.0,
                "model": "gpt-4o",
                "test_mode": True
            }
        )
    )
    
    # Add aggregator to summarize results
    wf.add_node(
        ToolNodeConfig(
            id="summarize",
            name="Summarize Results",
            type="tool", 
            tool_name="aggregator",
            tool_args={"results": "{{ process_items.* }}"},
            dependencies=["process_items"]
        )
    )
    
    return wf


async def main():
    """Run the seller assistant workflow."""
    
    print("Building Seller Assistant workflow...")
    workflow = await build_seller_workflow()
    
    # Validate the workflow
    try:
        workflow.validate()
        print("✅ Workflow validated successfully!")
    except Exception as e:
        print(f"❌ Workflow validation failed: {e}")
        # The system should tell us exactly what's wrong
        return
    
    # Execute the workflow
    print("\nExecuting workflow...")
    try:
        result = await workflow.execute()
        
        # Extract the final output
        if hasattr(result, 'output'):
            output = result.output
        else:
            output = result
            
        print("\n✅ Workflow completed successfully!")
        print(f"\nResults: {json.dumps(output, indent=2)}")
        
    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        # The system should provide clear error messages about what went wrong


if __name__ == "__main__":
    asyncio.run(main())