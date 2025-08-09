"""Discovery API: tools, agents, workflows, chains, executors, and components.

Split into its own module to avoid monolithic `main.py` growth.
"""

from __future__ import annotations

from typing import Any, Dict, List, cast

from fastapi import APIRouter, Depends

from ice_api.dependencies import get_tool_service
from ice_api.security import is_agent_allowed, is_tool_allowed

router = APIRouter(prefix="/api/v1", tags=["discovery"])


@router.get("/tools", response_model=List[str])
async def list_tools(
    tool_service: Any = Depends(get_tool_service),
) -> List[str]:  # noqa: D401
    """Return all registered tool names."""
    all_tools = cast(List[str], tool_service.available_tools())
    return [t for t in all_tools if is_tool_allowed(t)]


@router.get("/agents", response_model=List[str])
async def list_agents() -> List[str]:  # noqa: D401
    """Return all registered agent names."""
    from ice_core.registry import registry

    return [a for a in registry._agents.keys() if is_agent_allowed(a)]


@router.get("/workflows", response_model=List[str])
async def list_workflows() -> List[str]:  # noqa: D401
    """Return all registered workflow names."""
    from ice_core.models import NodeType
    from ice_core.registry import registry

    return [name for _, name in registry.list_nodes(NodeType.WORKFLOW)]


@router.get("/chains", response_model=List[str])
async def list_chains() -> List[str]:  # noqa: D401
    """Return all registered chain names."""
    from ice_core.registry import global_chain_registry

    return [name for name, _ in global_chain_registry.available_chains()]


@router.get("/executors", response_model=Dict[str, str])
async def list_executors() -> Dict[str, str]:  # noqa: D401
    """Return all registered executors keyed by node_type."""
    from ice_core.registry import registry

    return {k: v.__name__ for k, v in registry._executors.items()}


@router.get("/meta/components", response_model=Dict[str, Any])
async def meta_components() -> Dict[str, Any]:  # noqa: D401
    """Return component inventories for dashboards (names only)."""
    from ice_core.models.enums import NodeType
    from ice_core.registry import global_agent_registry, registry

    return {
        "tools": [n for _, n in registry.list_nodes(NodeType.TOOL)],
        "agents": [n for n, _ in global_agent_registry.available_agents()],
        "workflows": [n for _, n in registry.list_nodes(NodeType.WORKFLOW)],
    }
