"""Debug the full executor flow."""

import asyncio
from ice_core.models.node_models import ToolNodeConfig, LoopNodeConfig
from ice_orchestrator.workflow import Workflow
import ice_orchestrator  # Register executors

# Patch NodeExecutor to see what happens
from ice_orchestrator.execution.executor import NodeExecutor

# Store original
_original_execute = NodeExecutor.execute_node

async def debug_execute_node(self, node_id, input_data):
    """Debug wrapper for execute_node."""
    print(f"\n=== NodeExecutor.execute_node ===")
    print(f"Node ID: {node_id}")
    node = self.chain.nodes.get(node_id)
    print(f"Node type: {getattr(node, 'type', 'UNKNOWN')}")
    
    # Call original
    result = await _original_execute(self, node_id, input_data)
    
    print(f"Result success: {result.success}")
    print(f"Result error: {result.error}")
    print(f"Result output: {result.output}")
    
    return result

# Monkey patch
NodeExecutor.execute_node = debug_execute_node

# Simple tools
from ice_core.base_tool import ToolBase
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType
from typing import Any, Dict

class SimpleDataTool(ToolBase):
    name: str = "simple_data"
    description: str = "Provide simple data"
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        print("\nSimpleDataTool called")
        return {"rows": [{"name": "A"}, {"name": "B"}]}

class SimpleProcessTool(ToolBase):
    name: str = "simple_process"
    description: str = "Process item"
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        print(f"\nSimpleProcessTool called with: {list(kwargs.keys())}")
        item = kwargs.get("item", {})
        print(f"Item: {item}")
        return {"processed": item.get("name", "unknown")}
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        return {"type": "object", "additionalProperties": True}

# Register
registry.register_instance(NodeType.TOOL, "simple_data", SimpleDataTool(), validate=False)
registry.register_instance(NodeType.TOOL, "simple_process", SimpleProcessTool(), validate=False)

async def main():
    # Nodes
    data = ToolNodeConfig(
        id="data",
        name="Get Data",
        type="tool",
        tool_name="simple_data",
        tool_args={},
        dependencies=[]
    )
    
    process = ToolNodeConfig(
        id="process",
        name="Process",
        type="tool", 
        tool_name="simple_process",
        tool_args={},
        dependencies=[]
    )
    
    loop = LoopNodeConfig(
        id="loop",
        name="Process Loop",
        type="loop",
        items_source="data.rows",
        item_var="item",
        body=[process],
        dependencies=["data"]
    )
    
    # Workflow
    wf = Workflow(
        nodes=[data, loop],
        name="Debug Flow"
    )
    
    print("Starting execution...")
    result = await wf.execute()
    
    print(f"\n\nFinal output:")
    if hasattr(result, 'output'):
        for key, value in result.output.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    asyncio.run(main())