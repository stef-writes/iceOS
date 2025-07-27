"""Debug version of the Facebook Marketplace demo with detailed logging."""

import asyncio
import os
import structlog
from pathlib import Path

# Import our tools
from tools.read_inventory_csv import ReadInventoryCSVTool

# Import iceOS components
from ice_orchestrator.workflow import Workflow
from ice_core.models.node_models import ToolNodeConfig
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType


async def test_single_tool():
    """Test a single tool with manual execution to debug."""
    
    print("🧪 TESTING SINGLE TOOL EXECUTION")
    print("="*50)
    
    # Initialize iceOS first
    from ice_orchestrator import initialize_orchestrator
    initialize_orchestrator()
    
    # Register our tool
    tool = ReadInventoryCSVTool()
    registry.register_instance(NodeType.TOOL, "read_inventory_csv", tool)
    print(f"✅ Registered tool: {tool.name}")
    
    # Test direct tool call
    current_dir = Path(__file__).parent
    inventory_file = current_dir / "inventory.csv"
    
    print(f"📄 Testing direct tool call with file: {inventory_file}")
    
    try:
        # Test the way iceOS calls it
        merged_inputs = {"csv_file": str(inventory_file)}
        result = await tool.execute(merged_inputs)
        print(f"✅ Direct tool call successful!")
        print(f"📊 Result: {result.get('success')}, Items: {result.get('items_imported', 0)}")
        return result
        
    except Exception as e:
        print(f"❌ Direct tool call failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_workflow_execution():
    """Test workflow execution with detailed logging."""
    
    print("\n🔄 TESTING WORKFLOW EXECUTION")
    print("="*50)
    
    # Set up detailed logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Create single-node workflow
    current_dir = Path(__file__).parent
    inventory_file = current_dir / "inventory.csv"
    
    read_csv_node = ToolNodeConfig(
        id="read_csv",
        tool_name="read_inventory_csv",
        tool_args={"csv_file": str(inventory_file)},
        dependencies=[]
    )
    
    print(f"🔧 Creating workflow with node: {read_csv_node.id}")
    print(f"📋 Tool args: {read_csv_node.tool_args}")
    
    try:
        workflow = Workflow(
            nodes=[read_csv_node],
            name="Debug CSV Test",
            chain_id="debug_csv"
        )
        
        print("✅ Workflow created successfully")
        
        print("🚀 Executing workflow...")
        result = await workflow.execute()
        
        print(f"✅ Workflow execution completed!")
        print(f"📊 Result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
        
        # Check individual node results
        if isinstance(result, dict):
            for node_id, node_result in result.items():
                print(f"📋 Node {node_id}: {type(node_result)}")
                if hasattr(node_result, 'success'):
                    print(f"   Success: {node_result.success}")
                    if hasattr(node_result, 'error') and node_result.error:
                        print(f"   Error: {node_result.error}")
                elif isinstance(node_result, dict):
                    print(f"   Dict keys: {list(node_result.keys())}")
        else:
            # Single result case
            print(f"📊 Single result: {type(result)}")
            if hasattr(result, 'success'):
                print(f"   Success: {result.success}")
                if hasattr(result, 'error') and result.error:
                    print(f"   ❌ ERROR: {result.error}")
                if hasattr(result, 'output'):
                    print(f"   Output: {result.output}")
            else:
                print(f"   Raw result: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run debug tests."""
    
    print("🔬 FACEBOOK MARKETPLACE DEBUG SESSION")
    print("="*60)
    
    # Test 1: Direct tool execution
    tool_result = await test_single_tool()
    
    # Test 2: Workflow execution
    workflow_result = await test_workflow_execution()
    
    print("\n📋 DEBUG SUMMARY")
    print("="*30)
    print(f"Tool direct call: {'✅' if tool_result and tool_result.get('success') else '❌'}")
    print(f"Workflow execution: {'✅' if workflow_result else '❌'}")


if __name__ == "__main__":
    asyncio.run(main()) 