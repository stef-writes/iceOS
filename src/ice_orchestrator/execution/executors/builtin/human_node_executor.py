"""Executor for human nodes."""

from datetime import datetime
from typing import Dict

from ice_core.models import HumanNodeConfig, NodeExecutionResult
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry

__all__ = ["human_node_executor"]


@register_node("human")
async def human_node_executor(  # noqa: D401, ANN001
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: HumanNodeConfig,
    ctx: Dict[str, str],
) -> NodeExecutionResult:
    """Human approval executor.

    In production, a registered human approval implementation is required.
    Auto-approval fallback is allowed only in non-production environments.
    """
    start = datetime.utcnow()

    try:
        human_impl = registry.get_human_instance(getattr(cfg, "name", None) or cfg.id)
        response = await human_impl.execute(workflow=workflow, cfg=cfg, ctx=ctx)
    except KeyError:
        # No registered human implementation.
        # Allow auto-approval only outside production.
        import os

        env = os.getenv("ICE_ENV", os.getenv("ENV", "development")).lower()
        if env in {"production", "prod"}:
            return NodeExecutionResult(
                success=False,
                error=(
                    "HumanNode requires a registered implementation in production. "
                    "Register a human approval handler via registry.register_human_factory()."
                ),
                output={},
                metadata=NodeMetadata(
                    node_id=cfg.id,
                    node_type=cfg.type,
                    name="human_approval",
                    version="1.0.0",
                    owner="system",
                    provider=cfg.provider,
                    error_type="HumanApprovalMissing",
                    start_time=start,
                    end_time=datetime.utcnow(),
                    duration=(datetime.utcnow() - start).total_seconds(),
                    description="Human approval implementation missing in production",
                ),
            )

        response = {
            "approved": True,
            "response": "approved automatically by human-node executor",
        }

    end = datetime.utcnow()
    return NodeExecutionResult(
        success=True,
        output=response,
        metadata=NodeMetadata(
            node_id=cfg.id,
            node_type=cfg.type,
            name="human_approval",
            version="1.0.0",
            owner="system",
            provider=cfg.provider,
            error_type=None,
            start_time=start,
            end_time=end,
            duration=(end - start).total_seconds(),
            description="Human approval node execution",
        ),
    )
