"""Node catalog endpoints for studio/copilot consumption.

Provides typed metadata for available nodes with schemas where applicable.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field


class UIHints(BaseModel):
    """Optional UI rendering hints for studio forms."""

    widget: str | None = Field(default=None, description="Preferred widget type")
    placeholder: str | None = None
    enum: List[str] | None = None
    step: float | None = None


class ToolInfo(BaseModel):
    """Catalog entry for a Tool node.

    Attributes
    ----------
    name : str
        Registry name of the tool factory.
    input_schema : dict[str, Any]
        JSON Schema describing expected inputs.
    output_schema : dict[str, Any]
        JSON Schema describing outputs.
    ui_hints : dict[str, UIHints] | None
        Optional mapping of field name to UI hints.
    examples : list[dict[str, Any]] | None
        Example argument objects usable in studio.
    """

    name: str = Field(..., description="Registry name of the tool factory")
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    ui_hints: Dict[str, UIHints] | None = None
    examples: List[Dict[str, Any]] | None = None


class NodeCatalog(BaseModel):
    """High-level node catalog for authoring UIs and copilots."""

    tools: List[ToolInfo] = Field(default_factory=list)
    agents: List[str] = Field(default_factory=list)
    workflows: List[str] = Field(default_factory=list)
    chains: List[str] = Field(default_factory=list)


router = APIRouter(prefix="/api/v1/meta", tags=["discovery", "catalog"])


@router.get("/nodes", response_model=NodeCatalog)
async def list_node_catalog() -> NodeCatalog:  # noqa: D401
    """Return catalog of nodes with schemas for tools.

    Notes
    -----
    - Tool schemas are discovered from the registered tool factories.
    - Other node categories are listed by name at this tier (schemas are
      typically resolved at compile-time or via specialized endpoints).
    """

    from ice_api.security import is_tool_allowed
    from ice_core.models import NodeType
    from ice_core.registry import global_agent_registry, global_chain_registry, registry
    from ice_core.utils.node_conversion import discover_tool_schemas

    # Tools with schemas
    tools: List[ToolInfo] = []
    for name in registry.list_tools():
        if not is_tool_allowed(name):
            continue
        try:
            input_schema, output_schema = discover_tool_schemas(name)
        except Exception:
            # Be resilient – provide empty schemas if discovery fails
            input_schema, output_schema = (
                {"type": "object", "properties": {}},
                {
                    "type": "object",
                    "properties": {},
                },
            )
        # Minimal automatic UI hints: map enum and numeric ranges if present
        hints: Dict[str, UIHints] = {}
        props = (
            input_schema.get("properties", {}) if isinstance(input_schema, dict) else {}
        )
        for field, spec in props.items():
            if not isinstance(spec, dict):
                continue
            hint = UIHints()
            if "enum" in spec:
                hint.enum = [str(v) for v in spec.get("enum", [])]
                hint.widget = hint.widget or "select"
            if spec.get("type") in {"number", "integer"}:
                hint.widget = hint.widget or "number"
                if "multipleOf" in spec:
                    hint.step = float(spec["multipleOf"])  # best-effort
            if "examples" in spec and isinstance(spec["examples"], list):
                # we attach examples at top-level below; keep per-field placeholder if available
                if spec["examples"]:
                    hint.placeholder = str(spec["examples"][0])
            if any([hint.widget, hint.placeholder, hint.enum, hint.step]):
                hints[field] = hint

        examples: List[Dict[str, Any]] | None = None
        ex_vals = (
            input_schema.get("examples") if isinstance(input_schema, dict) else None
        )
        if isinstance(ex_vals, list) and ex_vals and isinstance(ex_vals[0], dict):
            examples = ex_vals  # type: ignore[assignment]

        tools.append(
            ToolInfo(
                name=name,
                input_schema=input_schema,
                output_schema=output_schema,
                ui_hints=hints or None,
                examples=examples,
            )
        )

    # Agents, Workflows, Chains by name
    agents = [n for n, _ in global_agent_registry.available_agents()]
    workflows = [n for _, n in registry.list_nodes(NodeType.WORKFLOW)]
    chains = [n for n, _ in global_chain_registry.available_chains()]

    return NodeCatalog(tools=tools, agents=agents, workflows=workflows, chains=chains)
