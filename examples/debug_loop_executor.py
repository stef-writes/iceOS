"""Debug the loop executor issue."""

import asyncio
from ice_core.models.node_models import ToolNodeConfig, LoopNodeConfig
from ice_orchestrator.workflow import Workflow
from ice_core.models import NodeExecutionResult
import ice_orchestrator  # Import to register executors
import ice_tools

# Simple data source tool
from ice_core.base_tool import ToolBase
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType
from typing import Any, Dict

class DataSourceTool(ToolBase):
    name: str = "data_source"
    description: str = "Provide test data"
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            "items": [
                {"name": "Item 1", "value": 100},
                {"name": "Item 2", "value": 200},
                {"name": "Item 3", "value": 300}
            ]
        }

class ProcessItemTool(ToolBase):
    name: str = "process_item"
    description: str = "Process a single item"
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        print(f"\nProcessItemTool received context keys: {list(kwargs.keys())}")
        item = kwargs.get("item")
        if item:
            print(f"Processing item: {item}")
            return {"processed": item, "doubled_value": item.get("value", 0) * 2}
        else:
            print("No item found in context!")
            return {"error": "No item found"}
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        return {"type": "object", "additionalProperties": True}

# Register tools
registry.register_instance(NodeType.TOOL, "data_source", DataSourceTool(), validate=False)
registry.register_instance(NodeType.TOOL, "process_item", ProcessItemTool(), validate=False)

async def main():
    # Create nodes
    data_node = ToolNodeConfig(
        id="get_data",
        name="Get Data",
        type="tool",
        tool_name="data_source",
        tool_args={},
        dependencies=[]
    )
    
    process_node = ToolNodeConfig(
        id="process",
        name="Process Item",
        type="tool",
        tool_name="process_item",
        tool_args={},
        dependencies=[]
    )
    
    loop_node = LoopNodeConfig(
        id="process_loop",
        name="Process Loop",
        type="loop",
        items_source="get_data.items",  # Nested path
        item_var="item",
        body=[process_node],
        dependencies=["get_data"]
    )
    
    # Create workflow
    wf = Workflow(
        nodes=[data_node, loop_node],
        name="Debug Loop",
        version="1.0"
    )
    
    # Validate
    print("Validating...")
    wf.validate()
    print("✅ Validation passed!")
    
    # Execute
    print("\nExecuting...")
    try:
        result = await wf.execute()
        print("\n✅ Execution completed!")
        
        # Print detailed results
        if hasattr(result, 'output'):
            output = result.output
            print(f"\nData source output: {output.get('get_data')}")
            print(f"\nLoop output: {output.get('process_loop')}")
        else:
            print(f"\nRaw result: {result}")
            
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())