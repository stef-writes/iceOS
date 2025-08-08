"""Executor for recursive nodes."""

from datetime import datetime
from typing import Any, Dict

from ice_core.models import (
    AgentNodeConfig,
    NodeExecutionResult,
    RecursiveNodeConfig,
    WorkflowNodeConfig,
)
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import get_executor, register_node, registry
from ice_core.utils.safe_eval import safe_eval_bool

__all__ = ["recursive_node_executor"]


@register_node("recursive")
async def recursive_node_executor(  # noqa: D401, ANN001
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: Any,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:
    """Execute a recursive node with convergence / iteration controls."""
    start_time = datetime.utcnow()

    try:
        # ------------------------------------------------------------
        # 1. Delegate to factory if registered -----------------------
        # ------------------------------------------------------------
        try:
            rec_impl = registry.get_recursive_instance(
                getattr(cfg, "name", None) or cfg.id
            )
            out = await rec_impl.execute(workflow=workflow, cfg=cfg, ctx=ctx)
            if isinstance(out, NodeExecutionResult):
                return out
            end_time = datetime.utcnow()
            return NodeExecutionResult(
                success=True,
                output=out,
                metadata=NodeMetadata(
                    node_id=getattr(cfg, "id", "recursive"),
                    node_type="recursive",
                    name=getattr(cfg, "name", "recursive_node"),
                    version="1.0.0",
                    owner="system",
                    provider=getattr(cfg, "provider", None),
                    error_type=None,
                    start_time=start_time,
                    end_time=end_time,
                    duration=(end_time - start_time).total_seconds(),
                    description="Recursive execution (factory)",
                ),
            )
        except KeyError:
            pass

        # ------------------------------------------------------------
        # 2. Normalise configuration --------------------------------
        # ------------------------------------------------------------
        recursive_cfg: RecursiveNodeConfig
        if isinstance(cfg, RecursiveNodeConfig):
            recursive_cfg = cfg
        else:
            recursive_cfg = RecursiveNodeConfig(**cfg.__dict__)

        iteration = ctx.get("_recursive_iteration", 0)
        context_key = recursive_cfg.context_key

        # ------------------------------------------------------------
        # 3. Safety guard – max_iterations ---------------------------
        # ------------------------------------------------------------
        if iteration >= recursive_cfg.max_iterations:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            return NodeExecutionResult(
                success=True,
                output={
                    "converged": False,
                    "reason": "max_iterations_reached",
                    "iterations": iteration,
                    "final_context": ctx.get(context_key, {}),
                },
                execution_time=duration,
                metadata=NodeMetadata(
                    node_id=recursive_cfg.id,
                    node_type=recursive_cfg.type,
                    name=recursive_cfg.name or "recursive_node",
                    version="1.0.0",
                    owner="system",
                    provider=recursive_cfg.provider,
                    error_type=None,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    description=f"Recursive execution: max iterations reached ({iteration})",
                ),
            )

        # ------------------------------------------------------------
        # 4. Check convergence condition ----------------------------
        # ------------------------------------------------------------
        if recursive_cfg.convergence_condition:
            try:
                converged = safe_eval_bool(recursive_cfg.convergence_condition, ctx)
                if converged:
                    end_time = datetime.utcnow()
                    duration = (end_time - start_time).total_seconds()
                    return NodeExecutionResult(
                        success=True,
                        output={
                            "converged": True,
                            "reason": "condition_met",
                            "iterations": iteration,
                            "final_context": ctx.get(context_key, {}),
                        },
                        execution_time=duration,
                        metadata=NodeMetadata(
                            node_id=recursive_cfg.id,
                            node_type=recursive_cfg.type,
                            name=recursive_cfg.name or "recursive_node",
                            version="1.0.0",
                            owner="system",
                            provider=recursive_cfg.provider,
                            error_type=None,
                            start_time=start_time,
                            end_time=end_time,
                            duration=duration,
                            description=f"Recursive execution: converged after {iteration} iterations",
                        ),
                    )
            except Exception as exc:  # pragma: no cover – warn & continue
                print(f"Warning: convergence condition failed: {exc}")

        # ------------------------------------------------------------
        # 5. Prepare next-iteration context -------------------------
        # ------------------------------------------------------------
        enhanced_ctx = ctx.copy()
        enhanced_ctx["_recursive_iteration"] = iteration + 1
        if recursive_cfg.preserve_context:
            enhanced_ctx.setdefault(context_key, {})
            enhanced_ctx[context_key]["iteration"] = iteration + 1
            enhanced_ctx[context_key]["node_id"] = recursive_cfg.id

        # ------------------------------------------------------------
        # 6. Execute inner agent or workflow ------------------------
        # ------------------------------------------------------------
        if recursive_cfg.agent_package:
            agent_cfg = AgentNodeConfig(
                id=recursive_cfg.id,
                name="recursive_agent",
                package=recursive_cfg.agent_package,
                max_iterations=10,
            )
            agent_exec = get_executor("agent")
            result = await agent_exec(workflow, agent_cfg, enhanced_ctx)
        elif recursive_cfg.workflow_ref:
            wf_cfg = WorkflowNodeConfig(
                id=recursive_cfg.id,
                name="recursive_workflow",
                workflow_ref=recursive_cfg.workflow_ref,
            )
            wf_exec = get_executor("workflow")
            result = await wf_exec(workflow, wf_cfg, enhanced_ctx)
        else:
            raise ValueError(
                f"Recursive node {recursive_cfg.id} must specify either agent_package or workflow_ref"
            )

        # ------------------------------------------------------------
        # 7. Annotate result with recursion metadata ----------------
        # ------------------------------------------------------------
        if isinstance(result.output, dict):
            result.output.update(
                {
                    "_recursive_iteration": iteration + 1,
                    "_can_recurse": True,
                    "_recursive_node_id": recursive_cfg.id,
                }
            )
            if recursive_cfg.preserve_context:
                result.output[context_key] = enhanced_ctx.get(context_key, {})

        end_time = datetime.utcnow()
        result.execution_time = (end_time - start_time).total_seconds()
        return result

    except Exception as exc:  # pragma: no cover
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        return NodeExecutionResult(
            success=False,
            error=str(exc),
            output={"error": str(exc)},
            execution_time=duration,
            metadata=NodeMetadata(
                node_id=getattr(cfg, "id", "recursive_unknown"),
                node_type="recursive",
                name=getattr(cfg, "name", "recursive_node"),
                version="1.0.0",
                owner="system",
                error_type=type(exc).__name__,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                provider=getattr(cfg, "provider", None),
                description=f"Recursive execution failed: {exc}",
            ),
        )
