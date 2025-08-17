"""Node-type deep-dive endpoints.

These endpoints expose per-node-type JSON Schemas and detailed tool entries
for studio UIs and AI copilots to render precise configuration forms.
"""

from __future__ import annotations

from typing import Any, Dict, List, Type

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ice_core.models import (
    AgentNodeConfig,
    CodeNodeConfig,
    ConditionNodeConfig,
    HumanNodeConfig,
    LLMNodeConfig,
    LoopNodeConfig,
    MonitorNodeConfig,
    ParallelNodeConfig,
    RecursiveNodeConfig,
    SwarmNodeConfig,
    ToolNodeConfig,
    WorkflowNodeConfig,
)

# Reuse ToolInfo from catalog to avoid duplication
from .catalog import ToolInfo


class NodeSchema(BaseModel):
    """Pydantic JSON Schema for a node configuration class."""

    type: str = Field(..., description="Canonical node type")
    json_schema: Dict[str, Any] = Field(..., description="Pydantic JSON Schema")


router = APIRouter(prefix="/api/v1/meta/nodes", tags=["catalog", "schemas"])


_TYPE_TO_MODEL: dict[str, Type[BaseModel]] = {
    "tool": ToolNodeConfig,
    "llm": LLMNodeConfig,
    "agent": AgentNodeConfig,
    "condition": ConditionNodeConfig,
    "workflow": WorkflowNodeConfig,
    "loop": LoopNodeConfig,
    "parallel": ParallelNodeConfig,
    "recursive": RecursiveNodeConfig,
    "code": CodeNodeConfig,
    "human": HumanNodeConfig,
    "monitor": MonitorNodeConfig,
    "swarm": SwarmNodeConfig,
}


@router.get("/types", response_model=List[str])
async def list_node_types() -> List[str]:  # noqa: D401
    """Return supported node type strings (canonical)."""

    return sorted(_TYPE_TO_MODEL.keys())


@router.get("/{node_type}/schema", response_model=NodeSchema)
async def get_node_schema(node_type: str) -> NodeSchema:  # noqa: D401
    """Return Pydantic JSON Schema for the given node type."""

    model = _TYPE_TO_MODEL.get(node_type)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Unknown node type: {node_type}")
    schema = model.model_json_schema()  # Pydantic v2
    return NodeSchema(type=node_type, json_schema=schema)


@router.get("/tool/{tool_name}", response_model=ToolInfo)
async def get_tool_details(tool_name: str) -> ToolInfo:  # noqa: D401
    """Return detailed info for a tool, including discovered schemas."""

    from ice_core.utils.node_conversion import discover_tool_schemas

    input_schema, output_schema = discover_tool_schemas(tool_name)
    return ToolInfo(
        name=tool_name, input_schema=input_schema, output_schema=output_schema
    )
