"""Executor for tool nodes."""

from datetime import datetime
from typing import Any, Dict

from ice_core.models import NodeExecutionResult, ToolNodeConfig
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry
from ice_orchestrator.execution.executors.builtin.helpers import (
    flatten_dependency_outputs,
    resolve_jinja_templates,
)
from ice_orchestrator.execution.sandbox.resource_sandbox import ResourceSandbox

__all__ = ["tool_node_executor"]


@register_node("tool")
async def tool_node_executor(
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: ToolNodeConfig,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:  # noqa: D401, ANN401
    """Execute a Tool node in the current workflow.

    The logic is identical to the legacy implementation that previously lived in
    `execution.executors.unified.tool_executor`, but now resides in the proper
    per-node executor module.
    """
    start_time = datetime.utcnow()

    try:
        # ------------------------------------------------------------------
        # 1. Ensure tools are registered (auto-import ice_tools package) -----
        # ------------------------------------------------------------------
        try:
            import ice_tools  # noqa: F401 – side-effect registration
        except ModuleNotFoundError:
            # `ice_tools` package is optional in minimal deployments.
            pass

        # ------------------------------------------------------------------
        # 2. Retrieve concrete Tool instance from the registry --------------
        # ------------------------------------------------------------------
        # Instantiate tool without per-run arguments; pass args only to execute()
        tool = registry.get_tool_instance(cfg.tool_name)

        # ------------------------------------------------------------------
        # 3. Prepare a clean context & resolve Jinja templates --------------
        # ------------------------------------------------------------------
        from ice_core.models import (
            NodeExecutionResult as _NER,  # local import to avoid cycles
        )

        ctx_clean: Dict[str, Any] = {
            k: (v.output if isinstance(v, _NER) and v.output is not None else v)
            for k, v in ctx.items()
        }

        resolved_tool_args = resolve_jinja_templates(cfg.tool_args or {}, ctx_clean)

        # Merge DAG context with explicit tool args and flatten helpful paths
        merged_inputs = {**resolved_tool_args, **ctx_clean}
        flattened_inputs = flatten_dependency_outputs(merged_inputs, tool)

        # ------------------------------------------------------------------
        # 4. Respect tool signature – pass only accepted parameters ---------
        # ------------------------------------------------------------------
        import inspect

        sig = inspect.signature(getattr(tool, "_execute_impl"))
        accepted = set(sig.parameters) - {"self", "kwargs"}
        safe_inputs = (
            {k: v for k, v in flattened_inputs.items() if k in accepted}
            if accepted
            else flattened_inputs
        )

        # ------------------------------------------------------------------
        # 5. Execute within the shared resource sandbox ---------------------
        # ------------------------------------------------------------------
        async with ResourceSandbox(timeout_seconds=cfg.timeout_seconds or 30):  # type: ignore[attr-defined]
            tool_output: Any = await tool.execute(**safe_inputs)

        # ------------------------------------------------------------------
        # 6. Normalise output back to plain dict ----------------------------
        # ------------------------------------------------------------------
        if isinstance(tool_output, _NER):
            tool_output = tool_output.output or (
                {"error": tool_output.error} if tool_output.error else {}
            )
        elif not isinstance(tool_output, dict):
            tool_output = {"result": tool_output}

        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=True,
            output=tool_output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.tool_name,
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"Tool execution: {cfg.tool_name}",
            ),
        )

    except Exception as exc:  # pragma: no cover – defensive
        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=False,
            error=str(exc),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.tool_name,
                version="1.0.0",
                owner="system",
                error_type=type(exc).__name__,
                provider=cfg.provider,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"Tool execution failed: {cfg.tool_name}",
            ),
        )
