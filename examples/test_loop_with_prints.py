"""Test loop with print debugging."""

import asyncio
from ice_core.models.node_models import ToolNodeConfig, LoopNodeConfig
from ice_orchestrator.workflow import Workflow
import ice_orchestrator  # Import to register executors

# Patch executor to add logging
from ice_core.unified_registry import registry
original_loop_exec = registry.get_executor("loop")

async def debug_loop_executor(workflow, cfg, ctx):
    print(f"\n=== LOOP EXECUTOR CALLED ===")
    print(f"Config ID: {cfg.id}")
    print(f"Items source: {getattr(cfg, 'items_source', 'NO ATTR')}")
    print(f"Context keys: {list(ctx.keys())}")
    
    try:
        result = await original_loop_exec(workflow, cfg, ctx)
        print(f"Loop result type: {type(result)}")
        print(f"Loop result: {result}")
        return result
    except Exception as e:
        print(f"Loop exception: {type(e).__name__}: {e}")
        raise

# Replace executor
registry._executors["loop"] = debug_loop_executor

# Also patch NodeExecutor
from ice_orchestrator.execution.executor import NodeExecutor
original_execute = NodeExecutor.execute_node

async def debug_execute_node(self, node_id, input_data):
    node = self.chain.nodes.get(node_id)
    print(f"\n--- NodeExecutor.execute_node called ---")
    print(f"Node ID: {node_id}")
    print(f"Node type: {getattr(node, 'type', 'NO TYPE')}")
    result = await original_execute(self, node_id, input_data)
    print(f"Execute result: {result}")
    return result

NodeExecutor.execute_node = debug_execute_node

# Simple test
from ice_core.base_tool import ToolBase
from ice_core.models.enums import NodeType
from typing import Any, Dict

class DataTool(ToolBase):
    name: str = "data"
    description: str = "Provide data"
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        return {"items": [{"x": 1}, {"x": 2}]}

class EchoTool(ToolBase):
    name: str = "echo"
    description: str = "Echo"
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        return {"echoed": kwargs.get("item", "nothing")}
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        return {"type": "object", "additionalProperties": True}

# Register
registry.register_instance(NodeType.TOOL, "data", DataTool(), validate=False)
registry.register_instance(NodeType.TOOL, "echo", EchoTool(), validate=False)

async def main():
    data_node = ToolNodeConfig(
        id="data",
        name="Data",
        type="tool",
        tool_name="data",
        tool_args={},
        dependencies=[]
    )
    
    echo_node = ToolNodeConfig(
        id="echo",
        name="Echo",
        type="tool",
        tool_name="echo",
        tool_args={},
        dependencies=[]
    )
    
    loop_node = LoopNodeConfig(
        id="loop",
        name="Loop",
        type="loop",
        items_source="data.items",
        item_var="item",
        body=[echo_node],
        dependencies=["data"]
    )
    
    wf = Workflow(nodes=[data_node, loop_node], name="Test")
    
    print("Starting execution...")
    result = await wf.execute()
    
    print(f"\n\nFinal result: {result.output}")

if __name__ == "__main__":
    asyncio.run(main())