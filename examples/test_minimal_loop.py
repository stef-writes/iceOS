"""Minimal test to debug loop execution."""

import asyncio
from ice_core.models.node_models import ToolNodeConfig, LoopNodeConfig
from ice_orchestrator.workflow import Workflow
import ice_tools
from ice_tools.toolkits.ecommerce import EcommerceToolkit
EcommerceToolkit(test_mode=True, upload=False).register()

async def main():
    # Create a simple echo tool for testing
    from ice_core.base_tool import ToolBase
    from ice_core.unified_registry import registry
    from ice_core.models.enums import NodeType
    from typing import Any, Dict
    
    class EchoTool(ToolBase):
        name: str = "echo"
        description: str = "Echo the input"
        
        async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
            print(f"Echo tool received: {kwargs}")
            # Extract the item
            item = kwargs.get("item", "No item found")
            print(f"Item: {item}")
            return {"echoed": item, "all_context": list(kwargs.keys())}
        
        @classmethod
        def get_input_schema(cls) -> Dict[str, Any]:
            return {"type": "object", "additionalProperties": True}
    
    # Register the echo tool
    echo_instance = EchoTool()
    registry.register_instance(NodeType.TOOL, echo_instance.name, echo_instance, validate=False)
    
    # Create nodes
    echo_node = ToolNodeConfig(
        id="echo",
        name="Echo",
        type="tool",
        tool_name="echo",
        tool_args={},
        dependencies=[]
    )
    
    loop_node = LoopNodeConfig(
        id="test_loop",
        name="Test Loop",
        type="loop",
        items_source="test_items",
        item_var="item",
        body=[echo_node],
        dependencies=[]
    )
    
    # Create workflow with initial context
    wf = Workflow(
        nodes=[loop_node],
        name="Test Loop",
        initial_context={"test_items": [{"value": 1}, {"value": 2}, {"value": 3}]}
    )
    
    # Validate
    print("Validating...")
    wf.validate()
    print("✅ Validation passed!")
    
    # Execute
    print("\nExecuting...")
    try:
        result = await wf.execute()
        print("✅ Execution completed!")
        print(f"\nResult: {result.output}")
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())