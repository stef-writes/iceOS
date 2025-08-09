"""Executor for agent nodes."""

from datetime import datetime
from typing import Any, Dict

from ice_core.models import AgentNodeConfig, NodeExecutionResult
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry
from ice_orchestrator.services.agent_runtime import AgentRuntime

__all__ = ["agent_node_executor"]


@register_node("agent")
async def agent_node_executor(
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: AgentNodeConfig,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:  # noqa: D401, ANN401
    """Execute an Agent node.

    Behaviour is identical to the original implementation but now self-contained
    in the dedicated executor module.
    """
    start_time = datetime.utcnow()

    try:
        # ------------------------------------------------------------------
        # 1. Obtain a fresh agent instance via registry ---------------------
        # ------------------------------------------------------------------
        agent: Any = registry.get_agent_instance(cfg.package)

        # ------------------------------------------------------------------
        # 2. Execute agent – trusted code has full DAG context --------------
        # ------------------------------------------------------------------
        runtime = AgentRuntime()
        agent_output: Any = await runtime.run(
            agent, context=ctx, max_iterations=cfg.max_iterations
        )

        if not isinstance(agent_output, dict):
            agent_output = {"result": agent_output}

        agent_output["agent_package"] = cfg.package
        agent_output["agent_executed"] = True

        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=True,
            output=agent_output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.package,
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"Agent execution: {cfg.package}",
            ),
        )

    except Exception as exc:  # pragma: no cover
        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=False,
            error=str(exc),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.package,
                version="1.0.0",
                owner="system",
                error_type=type(exc).__name__,
                provider=cfg.provider,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"Agent execution failed: {cfg.package}",
            ),
        )
