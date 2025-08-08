"""Executor for condition nodes."""

from datetime import datetime
from typing import Any, Dict

from ice_core.models import ConditionNodeConfig, NodeExecutionResult
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry
from ice_core.utils.safe_eval import safe_eval_bool

__all__ = ["condition_node_executor"]


@register_node("condition")
async def condition_node_executor(
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: ConditionNodeConfig,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:  # noqa: D401, ANN401
    """Evaluate *cfg.expression* and execute the true/false branch inline."""
    start_time = datetime.utcnow()

    try:
        # --------------------------------------------------------------
        # 1. Evaluate via factory if registered, else safe_eval ---------
        # --------------------------------------------------------------
        try:
            cond = registry.get_condition_instance(cfg.name or cfg.id)
            result = await cond.evaluate(expression=cfg.expression, context=ctx)
        except KeyError:
            result = safe_eval_bool(cfg.expression, ctx)
        branch_nodes = cfg.true_path if result else cfg.false_path
        branch_name = "true" if result else "false"

        # --------------------------------------------------------------
        # 2. Execute selected branch nodes -----------------------------
        # --------------------------------------------------------------
        branch_outputs: Dict[str, Any] = {}
        if branch_nodes:
            branch_ctx = {**ctx, "condition_result": result}

            for node in branch_nodes:
                if hasattr(workflow, "execute_node_config"):
                    node_result = await workflow.execute_node_config(
                        node,
                        branch_ctx,
                        parent_id=cfg.id,
                    )
                    branch_outputs[node.id] = node_result.output
                    # Make each output available to subsequent nodes in branch
                    branch_ctx[node.id] = node_result.output

        # --------------------------------------------------------------
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        return NodeExecutionResult(
            success=True,
            output={
                "result": result,
                "branch": branch_name,
                "expression": cfg.expression,
                "branch_outputs": branch_outputs,
            },
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.name,
                version="1.0.0",
                owner="system",
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=None,
                provider=cfg.provider,
                description=f"Condition evaluated: {cfg.expression} -> {branch_name}",
            ),
            execution_time=duration,
        )

    except Exception as exc:  # pragma: no cover – defensive
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        return NodeExecutionResult(
            success=False,
            error=f"Failed to evaluate condition '{cfg.expression}': {exc}",
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.name,
                version="1.0.0",
                owner="system",
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(exc).__name__,
                provider=cfg.provider,
                description=f"Condition evaluation failed: {cfg.expression}",
            ),
            execution_time=duration,
        )
