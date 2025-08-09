"""Registry health and completeness diagnostics for Node Engineering Studio."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from ice_core.models import NodeType
from ice_core.unified_registry import registry

router = APIRouter(prefix="/api/v1/meta/registry", tags=["discovery", "health"])


@router.get("/health")
async def registry_health() -> Dict[str, Any]:  # noqa: D401
    """Return counts and missing executor information.

    This endpoint helps ensure the orchestrator registry is fully populated and
    matches expectations after initialization and policy filtering.
    """

    tools = registry.list_tools()
    agents: List[str] = []
    try:
        from ice_core.registry import global_agent_registry

        agents = [n for n, _ in global_agent_registry.available_agents()]
    except Exception:
        agents = []

    missing_exec: List[str] = []
    try:
        for nt in NodeType:
            try:
                registry.get_executor(nt.value)  # type: ignore[arg-type]
            except Exception:
                missing_exec.append(nt.value)
    except Exception:
        pass

    return {
        "tools_count": len(tools),
        "agents_count": len(agents),
        "missing_executors": missing_exec,
        "tools": tools,
        "agents": agents,
    }
