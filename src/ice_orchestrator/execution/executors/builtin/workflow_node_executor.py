"""Executor for *workflow* nodes – fully migrated from `unified.py`."""

from datetime import datetime
from typing import Any, Dict, cast

from ice_core.models import NodeExecutionResult, WorkflowNodeConfig
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry

__all__ = ["workflow_node_executor"]


@register_node("workflow")
async def workflow_node_executor(
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: Any,  # Accept loose configs for forward-compat
    ctx: Dict[str, Any],
) -> NodeExecutionResult:  # noqa: D401, ANN401
    """Execute a sub-workflow referenced by *cfg.workflow_ref*.

    Mirrors the legacy implementation but is now colocated in the granular
    executor module.
    """
    start_time = datetime.utcnow()

    try:
        # --------------------------------------------------------------
        # 1. Resolve the referenced workflow --------------------------
        # --------------------------------------------------------------
        if isinstance(cfg, WorkflowNodeConfig):
            workflow_ref = cfg.workflow_ref
        else:
            workflow_ref_str: Any = getattr(cfg, "workflow_ref", None)
            if not isinstance(workflow_ref_str, str):
                raise ValueError(f"Workflow node {cfg.id} missing workflow_ref")
            workflow_ref = workflow_ref_str

        # Prefer factory-based workflow registration if present
        sub_workflow = registry.get_workflow_instance(workflow_ref)

        # --------------------------------------------------------------
        # 2. Merge context with optional overrides --------------------
        # --------------------------------------------------------------
        merged_ctx = {**ctx}
        if getattr(cfg, "config_overrides", None):  # type: ignore[attr-defined]
            merged_ctx.update(cfg.config_overrides)  # type: ignore[attr-defined]

        # --------------------------------------------------------------
        # 3. Execute the child workflow --------------------------------
        # --------------------------------------------------------------
        # Cast to Any to call execute – WorkflowLike protocol omits it to avoid cycles
        sub_result = await cast(Any, sub_workflow).execute(merged_ctx)

        # Normalise to dict output
        if isinstance(sub_result, NodeExecutionResult):
            result_dict: Dict[str, Any] = cast(
                Dict[str, Any],
                (
                    sub_result.output
                    if sub_result.success
                    else {"error": sub_result.error}
                ),
            )
        else:
            result_dict = sub_result  # type: ignore[assignment]

        # Handle exposed outputs mapping ----------------------------------
        output: Dict[str, Any] | Any = result_dict
        if getattr(cfg, "exposed_outputs", None):  # type: ignore[attr-defined]
            exposed: Dict[str, Any] = {}
            for external_name, internal_path in cfg.exposed_outputs.items():  # type: ignore[attr-defined]
                value: Any = result_dict
                for part in internal_path.split("."):
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
                exposed[external_name] = value
            output = exposed

        # --------------------------------------------------------------
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        return NodeExecutionResult(
            success=True,
            output=output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=getattr(cfg, "name", None),
                version="1.0.0",
                owner="system",
                provider=getattr(cfg, "provider", None),
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                description=f"Workflow execution: {workflow_ref}",
            ),
            execution_time=duration,
        )

    except Exception as exc:  # pragma: no cover
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        return NodeExecutionResult(
            success=False,
            error=str(exc),
            output={},
            metadata=NodeMetadata(
                node_id=getattr(cfg, "id", "workflow_error"),
                node_type=getattr(cfg, "type", "workflow"),
                name=getattr(cfg, "name", None),
                version="1.0.0",
                owner="system",
                provider=getattr(cfg, "provider", None),
                error_type=type(exc).__name__,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                description=f"Workflow execution failed: {getattr(cfg, 'workflow_ref', 'unknown')}",
            ),
            execution_time=duration,
        )
