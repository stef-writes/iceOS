from __future__ import annotations

"""Utility helpers for converting design-time MCP *NodeSpec* objects into
runtime *NodeConfig* objects.

Keeping this logic inside *ice_core* prevents higher-level layers from
hard-coding type switches and ensures that the mapping stays in one place.
"""

from typing import Dict, List, Type, Any

from ice_core.models import (
    ConditionNodeConfig,
    LLMOperatorConfig,
    NodeConfig,
    ToolNodeConfig,
    AgentNodeConfig,
    NestedChainConfig,
)

__all__: list[str] = [
    "convert_node_spec",
    "convert_node_specs",
]

# ---------------------------------------------------------------------------
# Internal registry ---------------------------------------------------------
# ---------------------------------------------------------------------------

_NODE_TYPE_MAP: Dict[str, Type[NodeConfig]] = {
    # Deterministic tool ---------------------------------------------
    "tool": ToolNodeConfig,

    # LLM operator ----------------------------------------------------------
    "llm": LLMOperatorConfig,

    # Agent -----------------------------------------------------------------
    "agent": AgentNodeConfig,

    # Control-flow ----------------------------------------------------------
    "condition": ConditionNodeConfig,
    "nested_chain": NestedChainConfig,
}

# ---------------------------------------------------------------------------
# Public API -----------------------------------------------------------------
# ---------------------------------------------------------------------------

def convert_node_spec(spec: Any) -> NodeConfig:
    """Convert a single *NodeSpec* into its concrete :class:`NodeConfig`.

    The incoming object should have at minimum an ``id`` and ``type`` field.
    Subtype fields (``tool_args``, ``prompt``, etc.) are passed through during
    model validation.

    Parameters
    ----------
    spec : NodeSpec
        A MCP node specification object.

    Returns
    -------
    NodeConfig
        A fully validated runtime configuration object.

    Raises
    ------
    ValueError
        If the *type* field is missing or unknown.
    """
    # Import here to avoid circular dependency
    from ice_core.models.mcp import NodeSpec
    
    # Ensure we have a NodeSpec
    if not isinstance(spec, NodeSpec):
        raise ValueError("Expected NodeSpec instance")

    payload = spec.model_dump()
    node_type = payload.get("type")
    if not node_type:
        raise ValueError("NodeSpec.type is required for conversion")

# Alias handling removed – v1.1 now rejects *any* non-canonical node type.

    cfg_cls = _NODE_TYPE_MAP.get(node_type)
    if cfg_cls is None:
        raise ValueError(f"Unknown node type '{node_type}'")

    return cfg_cls.model_validate(payload)

def convert_node_specs(specs: List[Any]) -> List[NodeConfig]:
    """Bulk convert a list of NodeSpec objects."""

    return [convert_node_spec(s) for s in specs]
