"""Debug loop with added logging."""

import asyncio
import logging
logging.basicConfig(level=logging.DEBUG)

from ice_core.models.node_models import ToolNodeConfig, LoopNodeConfig
from ice_orchestrator.workflow import Workflow
from ice_core.models import NodeExecutionResult, NodeMetadata
from datetime import datetime

# Patch the loop executor to add logging
from ice_orchestrator.execution.executors.unified import _registry
original_loop_executor = _registry["loop"]

async def debug_loop_executor(workflow, cfg, ctx):
    """Wrapped loop executor with debugging."""
    print(f"\n=== DEBUG LOOP EXECUTOR ===")
    print(f"Config: {cfg}")
    print(f"Config type: {type(cfg)}")
    print(f"Config ID: {cfg.id}")
    print(f"Items source: {getattr(cfg, 'items_source', 'NO ITEMS SOURCE')}")
    print(f"Context keys: {list(ctx.keys())}")
    
    # Call original
    try:
        result = await original_loop_executor(workflow, cfg, ctx)
        print(f"Loop executor returned: {result}")
        print(f"Result type: {type(result)}")
        return result
    except Exception as e:
        print(f"Loop executor exception: {e}")
        import traceback
        traceback.print_exc()
        raise

# Replace with debug version
_registry["loop"] = debug_loop_executor

# Now run the test
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
                {"name": "Item 2", "value": 200}
            ]
        }

class ProcessItemTool(ToolBase):
    name: str = "process_item"
    description: str = "Process a single item"
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        item = kwargs.get("item", "No item")
        return {"processed": str(item)}
    
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
        items_source="get_data.items",
        item_var="item",
        body=[process_node],
        dependencies=["get_data"]
    )
    
    # Create workflow
    wf = Workflow(
        nodes=[data_node, loop_node],
        name="Debug Loop"
    )
    
    print("Executing workflow...")
    try:
        result = await wf.execute()
        print(f"\nFinal result: {result}")
        if hasattr(result, 'output'):
            print(f"Output: {result.output}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())