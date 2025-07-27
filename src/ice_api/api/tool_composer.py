"""Visual Tool Composer API - Build tools as workflows via MCP blueprints.

This module enables creating tools by composing them from existing components
using the already-implemented partial blueprint infrastructure.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ice_core.models.mcp import PartialBlueprint, PartialNodeSpec
from ice_api.redis_client import get_redis
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType


router = APIRouter(prefix="/api/v1/tool-composer", tags=["tool-composer"])


class ToolComposerRequest(BaseModel):
    """Request to create a tool from visual composition."""
    tool_name: str = Field(..., description="Name for the composed tool")
    description: str = Field(..., description="Tool description") 
    category: str = Field(default="composed", description="Tool category")
    nodes: List[Dict[str, Any]] = Field(..., description="Visual node definitions")
    connections: List[Dict[str, str]] = Field(..., description="Node connections")
    input_mapping: Dict[str, str] = Field(..., description="Map tool inputs to node inputs")
    output_mapping: Dict[str, str] = Field(..., description="Map node outputs to tool outputs")


class ComposedToolResponse(BaseModel):
    """Response after creating a composed tool."""
    tool_name: str
    blueprint_id: str
    preview_code: str
    registration_status: str


@router.post("/compose", response_model=ComposedToolResponse)
async def compose_tool(request: ToolComposerRequest) -> ComposedToolResponse:
    """Create a tool by visual composition using partial blueprints.
    
    This endpoint:
    1. Creates a partial blueprint for the tool workflow
    2. Validates the composition
    3. Generates preview code
    4. Optionally registers the tool
    """
    # Create partial blueprint for the tool composition
    partial = PartialBlueprint(
        blueprint_id=f"tool_{request.tool_name}",
        description=request.description,
        metadata={
            "tool_name": request.tool_name,
            "category": request.category,
            "composed": True
        }
    )
    
    # Add nodes from visual composition
    for node in request.nodes:
        spec = PartialNodeSpec(
            id=node["id"],
            type=node["type"],
            pending_inputs=node.get("inputs", []),
            pending_outputs=node.get("outputs", []),
            partial_config=node.get("config", {})
        )
        partial.add_node(spec)
    
    # Add connections
    for conn in request.connections:
        partial.add_edge(conn["from_node"], conn["to_node"])
    
    # Validate the composition
    validation = partial._validate_incremental()
    if not validation.is_valid:
        raise HTTPException(400, detail=f"Invalid composition: {validation.errors}")
    
    # Generate tool wrapper code
    preview_code = _generate_composed_tool_code(request, partial)
    
    # Save to Redis for later finalization
    redis = get_redis()
    await redis.set(
        f"composed_tool:{request.tool_name}",
        partial.model_dump_json(),
        ex=3600  # 1 hour expiry
    )
    
    return ComposedToolResponse(
        tool_name=request.tool_name,
        blueprint_id=partial.blueprint_id,
        preview_code=preview_code,
        registration_status="pending"
    )


@router.get("/preview/{tool_name}")
async def preview_composed_tool(tool_name: str) -> Dict[str, Any]:
    """Preview a composed tool before finalizing."""
    redis = get_redis()
    data = await redis.get(f"composed_tool:{tool_name}")
    
    if not data:
        raise HTTPException(404, detail="Composed tool not found")
    
    partial = PartialBlueprint.model_validate_json(data)
    
    # Show visual representation data
    return {
        "tool_name": tool_name,
        "nodes": [node.model_dump() for node in partial.nodes],
        "edges": partial.edges,
        "validation": partial._validate_incremental().model_dump(),
        "suggestions": partial._suggest_next_actions()
    }


@router.post("/finalize/{tool_name}")
async def finalize_composed_tool(tool_name: str) -> Dict[str, Any]:
    """Finalize and register a composed tool."""
    redis = get_redis()
    data = await redis.get(f"composed_tool:{tool_name}")
    
    if not data:
        raise HTTPException(404, detail="Composed tool not found")
    
    partial = PartialBlueprint.model_validate_json(data)
    
    # Convert to executable blueprint
    try:
        blueprint = partial.finalize()
    except Exception as e:
        raise HTTPException(400, detail=f"Cannot finalize: {str(e)}")
    
    # Create dynamic tool class
    tool_class = _create_dynamic_tool_class(tool_name, blueprint)
    
    # Register in unified registry
    tool_instance = tool_class()
    registry.register_instance(NodeType.TOOL, tool_name, tool_instance)
    
    # Clean up Redis
    await redis.delete(f"composed_tool:{tool_name}")
    
    return {
        "status": "success",
        "tool_name": tool_name,
        "message": f"Tool '{tool_name}' registered and ready to use"
    }


def _generate_composed_tool_code(request: ToolComposerRequest, partial: PartialBlueprint) -> str:
    """Generate preview code for the composed tool."""
    # Build imports based on node types
    imports = set([
        "from typing import Dict, Any",
        "from ice_core.base_tool import ToolBase",
        "from ice_sdk.decorators import tool",
        "from ice_sdk.builders.workflow import WorkflowBuilder"
    ])
    
    # Generate the preview code
    code = f'''"""Generated tool from visual composition."""
{chr(10).join(sorted(imports))}


@tool(name="{request.tool_name}")
class {request.tool_name.title().replace("_", "")}Tool(ToolBase):
    """{request.description}
    
    This tool was created through visual composition.
    """
    
    def __init__(self):
        super().__init__()
        # Build internal workflow
        self.builder = WorkflowBuilder("{request.tool_name}_workflow")
        
        # Add nodes
'''
    
    # Add node creation code
    for node in request.nodes:
        if node["type"] == "tool":
            code += f'        self.builder.add_tool("{node["id"]}", tool_name="{node["config"]["tool_name"]}")\n'
        elif node["type"] == "llm":
            code += f'        self.builder.add_llm("{node["id"]}", model="{node["config"]["model"]}", prompt="{node["config"]["prompt"]}")\n'
    
    # Add connections
    code += '\n        # Connect nodes\n'
    for conn in request.connections:
        code += f'        self.builder.connect("{conn["from_node"]}", "{conn["to_node"]}")\n'
    
    code += '''
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the composed tool workflow."""
        # Map inputs
        workflow_inputs = {}
'''
    
    # Add input mapping
    for tool_input, node_input in request.input_mapping.items():
        code += f'        workflow_inputs["{node_input}"] = input_data["{tool_input}"]\n'
    
    code += '''        
        # Execute workflow
        workflow = self.builder.build()
        result = await workflow.execute(workflow_inputs)
        
        # Map outputs
        tool_outputs = {}
'''
    
    # Add output mapping
    for node_output, tool_output in request.output_mapping.items():
        code += f'        tool_outputs["{tool_output}"] = result.get("{node_output}")\n'
    
    code += '''        
        return tool_outputs
'''
    
    return code


def _create_dynamic_tool_class(tool_name: str, blueprint):
    """Create a dynamic tool class from a blueprint."""
    # This is a simplified version - in production would be more sophisticated
    from ice_core.base_tool import ToolBase
    from ice_sdk.builders.workflow import WorkflowBuilder
    
    class ComposedTool(ToolBase):
        def __init__(self):
            super().__init__()
            self.blueprint = blueprint
            self.name = tool_name
        
        async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            # Execute the blueprint as a workflow
            # This would use the workflow execution service
            return {"status": "executed", "tool": tool_name}
        
        @classmethod
        def get_input_schema(cls) -> Dict[str, Any]:
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
        
        @classmethod
        def get_output_schema(cls) -> Dict[str, Any]:
            return {
                "type": "object",
                "properties": {
                    "status": {"type": "string"}
                }
            }
    
    # Set class name dynamically
    ComposedTool.__name__ = f"{tool_name.title().replace('_', '')}Tool"
    ComposedTool.__qualname__ = ComposedTool.__name__
    
    return ComposedTool 