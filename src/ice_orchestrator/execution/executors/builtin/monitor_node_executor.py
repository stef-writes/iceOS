"""Executor for monitor nodes."""

from datetime import datetime
from typing import Dict

from ice_core.models import MonitorNodeConfig, NodeExecutionResult
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry
from ice_core.utils.safe_eval import safe_eval_bool

__all__ = ["monitor_node_executor"]


@register_node("monitor")
async def monitor_node_executor(  # noqa: D401, ANN001
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: MonitorNodeConfig,
    ctx: Dict[str, str],
) -> NodeExecutionResult:
    """Evaluate metric expression and optionally trigger alerts (stub)."""
    start = datetime.utcnow()

    try:
        monitor_impl = registry.get_monitor_instance(
            getattr(cfg, "name", None) or cfg.id
        )
        impl_out = await monitor_impl.execute(workflow=workflow, cfg=cfg, ctx=ctx)
        triggered = (
            bool(impl_out.get("triggered", False))
            if isinstance(impl_out, dict)
            else False
        )
        if isinstance(impl_out, dict):
            output: Dict[str, str | bool | int | list[str]] = impl_out
        else:
            output = {"triggered": triggered}
    except KeyError:
        try:
            triggered = safe_eval_bool(cfg.metric_expression, ctx)
        except Exception:
            triggered = False
        output = {
            "metric_evaluated": cfg.metric_expression,
            "triggered": triggered,
            "triggers_fired": int(triggered),
            "checks_performed": 1,
        }
        if triggered:
            output["action_taken"] = cfg.action_on_trigger
            if cfg.action_on_trigger == "alert_only":
                output["alerts_sent"] = cfg.alert_channels or []

    end = datetime.utcnow()
    return NodeExecutionResult(
        success=True,
        output=output,
        metadata=NodeMetadata(
            node_id=cfg.id,
            node_type=cfg.type,
            name="monitor_node",
            version="1.0.0",
            owner="system",
            provider=cfg.provider,
            error_type=None,
            start_time=start,
            end_time=end,
            duration=(end - start).total_seconds(),
            description=f"Monitor execution: {cfg.metric_expression}",
        ),
    )
