"""Node-type deep-dive endpoints.

These endpoints expose per-node-type JSON Schemas and detailed tool entries
for studio UIs and AI copilots to render precise configuration forms.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

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


class LinkHintRequest(BaseModel):
    node_id: str
    target_prompt: Optional[str] = None
    target_args: Optional[Dict[str, Any]] = None
    upstream_ids: List[str] = Field(default_factory=list)


class LinkHintResponse(BaseModel):
    suggestions: List[str] = Field(
        default_factory=list,
        description="Placeholder roots to replace with an upstream id",
    )


class Port(BaseModel):
    name: str
    max: str = Field(description="one | many")


class NodeSchema(BaseModel):
    """Pydantic JSON Schema for a node configuration class."""

    type: str = Field(..., description="Canonical node type")
    json_schema: Dict[str, Any] = Field(..., description="Pydantic JSON Schema")
    ports: Dict[str, List[Port]] = Field(
        default_factory=dict,
        description="Declared port spec for UI enforcement (inputs/outputs).",
    )


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

    # Best-effort port spec by canonical type
    def _ports_for_type(nt: str) -> Dict[str, List[Port]]:
        if nt == "condition":
            return {
                "inputs": [Port(name="in", max="one")],
                "outputs": [
                    Port(name="true", max="one"),
                    Port(name="false", max="one"),
                ],
            }
        if nt == "parallel":
            return {
                "inputs": [Port(name="in", max="many")],
                "outputs": [Port(name="out", max="many")],
            }
        if nt == "loop":
            return {
                "inputs": [Port(name="in", max="one")],
                "outputs": [Port(name="body", max="one"), Port(name="out", max="one")],
            }
        # default single in/out for common nodes
        return {
            "inputs": [Port(name="in", max="many")],
            "outputs": [Port(name="out", max="many")],
        }

    return NodeSchema(
        type=node_type, json_schema=schema, ports=_ports_for_type(node_type)
    )


@router.get("/tool/{tool_name}", response_model=ToolInfo)
async def get_tool_details(tool_name: str) -> ToolInfo:  # noqa: D401
    """Return detailed info for a tool, including discovered schemas."""

    from ice_core.utils.node_conversion import discover_tool_schemas

    input_schema, output_schema = discover_tool_schemas(tool_name)
    return ToolInfo(
        name=tool_name, input_schema=input_schema, output_schema=output_schema
    )


@router.post("/link-hints", response_model=LinkHintResponse)
async def link_hints(payload: LinkHintRequest) -> LinkHintResponse:  # noqa: D401
    """Suggest unresolved placeholder roots to map from upstream outputs.

    Best-effort static analysis: extract {{ root.* }} tokens from target prompt/args
    and return roots not present in upstream_ids or 'inputs'.
    """

    def extract_roots(text: str) -> List[str]:
        import re

        keys = []
        for m in re.finditer(r"\{\{\s*([^}]+?)\s*\}\}", text or ""):
            k = (m.group(1) or "").strip()
            if not k:
                continue
            # root up to first '.' or '['
            dot = k.find(".")
            br = k.find("[")
            idxs = [i for i in [dot, br] if i >= 0]
            root = k[: min(idxs)] if idxs else k
            keys.append(root)
        return list(dict.fromkeys(keys))

    roots: List[str] = []
    if payload.target_prompt:
        roots.extend(extract_roots(payload.target_prompt))
    if isinstance(payload.target_args, dict):
        for v in payload.target_args.values():
            if isinstance(v, str):
                roots.extend(extract_roots(v))
    roots = list(dict.fromkeys(roots))
    available = set(["inputs", *payload.upstream_ids])
    suggestions = [r for r in roots if r not in available]
    return LinkHintResponse(suggestions=suggestions)
