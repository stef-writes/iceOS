"""Executor for swarm nodes."""

from datetime import datetime
from typing import Dict, List

from ice_core.models import NodeExecutionResult, SwarmNodeConfig
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry

__all__ = ["swarm_node_executor"]


@register_node("swarm")
async def swarm_node_executor(  # noqa: D401, ANN001
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: SwarmNodeConfig,
    ctx: Dict[str, str],
) -> NodeExecutionResult:
    """Minimal swarm executor – validates agent presence in registry."""
    start = datetime.utcnow()

    # Prefer factory if registered
    try:
        swarm_impl = registry.get_swarm_instance(getattr(cfg, "name", None) or cfg.id)
        out = await swarm_impl.execute(workflow=workflow, cfg=cfg, ctx=ctx)
        if isinstance(out, NodeExecutionResult):
            return out
        # Wrap plain dict into NodeExecutionResult
        end = datetime.utcnow()
        return NodeExecutionResult(
            success=True,
            output=out,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name="swarm_node",
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start,
                end_time=end,
                duration=(end - start).total_seconds(),
                description="Swarm execution (factory)",
            ),
        )
    except KeyError:
        pass

    missing: List[str] = []
    for agent in cfg.agents:
        try:
            registry.get_agent_import_path(agent.role)
        except KeyError:
            missing.append(agent.role)

    if missing:
        end = datetime.utcnow()
        return NodeExecutionResult(
            success=False,
            error=f"Agents not found in registry: {', '.join(missing)}",
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name="swarm_node",
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start,
                end_time=end,
                duration=(end - start).total_seconds(),
                description=f"Swarm execution failed: missing agents {missing}",
            ),
        )

    end = datetime.utcnow()
    return NodeExecutionResult(
        success=True,
        output={"swarm": "executed", "agents": [a.role for a in cfg.agents]},
        metadata=NodeMetadata(
            node_id=cfg.id,
            node_type=cfg.type,
            name="swarm_node",
            version="1.0.0",
            owner="system",
            provider=cfg.provider,
            error_type=None,
            start_time=start,
            end_time=end,
            duration=(end - start).total_seconds(),
            description="Swarm execution completed",
        ),
    )
