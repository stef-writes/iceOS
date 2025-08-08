"""Executor for loop nodes."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ice_core.models import LoopNodeConfig, NodeExecutionResult
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import get_executor, register_node, registry

__all__ = ["loop_node_executor"]


@register_node("loop")
async def loop_node_executor(  # noqa: D401, ANN001
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: Any,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:
    """Execute a *loop* node by iterating over items_source and running body."""
    start_time = datetime.utcnow()

    # ------------------------------------------------------------------
    # 1. If a loop factory is registered under cfg.name/id, delegate -----
    # ------------------------------------------------------------------
    try:
        loop_impl = registry.get_loop_instance(getattr(cfg, "name", None) or cfg.id)
        out = await loop_impl.execute(workflow=workflow, cfg=cfg, ctx=ctx)
        if isinstance(out, NodeExecutionResult):
            return out
        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=True,
            output=out,
            metadata=NodeMetadata(
                node_id=getattr(cfg, "id", "loop"),
                node_type="loop",
                name=getattr(cfg, "name", None),
                version="1.0.0",
                owner="system",
                provider=getattr(cfg, "provider", None),
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description="Loop execution (factory)",
            ),
        )
    except KeyError:
        pass

    # ------------------------------------------------------------------
    # 2. Normalise config ------------------------------------------------
    # ------------------------------------------------------------------
    iterator_path: Optional[str]
    item_var: str
    if isinstance(cfg, LoopNodeConfig):
        iterator_path = cfg.items_source
        max_iterations = cfg.max_iterations
        body = cfg.body
        item_var = cfg.item_var or "item"
    else:  # fallback for dict-like configs
        iterator_path = getattr(cfg, "items_source", None)
        max_iterations = getattr(cfg, "max_iterations", 100)
        body = getattr(cfg, "body", [])
        item_var = getattr(cfg, "item_var", "item")

    if not iterator_path:
        raise ValueError("Loop node missing items_source / iterator_path")

    # ------------------------------------------------------------------
    # 3. Resolve list of items -----------------------------------------
    # ------------------------------------------------------------------
    if hasattr(workflow, "_resolve_nested_path"):
        items = workflow._resolve_nested_path(ctx, iterator_path)  # type: ignore[attr-defined]
    else:
        items = ctx.get(iterator_path)

    if not isinstance(items, list):
        raise ValueError(f"Iterator path {iterator_path} did not resolve to a list")

    # ------------------------------------------------------------------
    # 4. Iterate and execute body ---------------------------------------
    # ------------------------------------------------------------------
    results: List[Any] = []
    for idx, item in enumerate(items[: max_iterations or len(items)]):
        item_ctx = {**ctx, item_var: item}
        last_out: Any = None

        for node in body:
            executor = get_executor(node.type)
            # Direct call – no hierarchical node-id mutation
            exec_result = await executor(workflow, node, item_ctx)
            last_out = (
                exec_result.output if hasattr(exec_result, "output") else exec_result
            )
            item_ctx[node.id] = last_out  # make output available to next node

        results.append(last_out)

    # make loop results accessible downstream
    ctx[cfg.id] = results  # type: ignore[index]

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    return NodeExecutionResult(
        success=True,
        output=results,
        metadata=NodeMetadata(
            node_id=cfg.id,
            node_type="loop",
            version="1.0.0",
            owner="system",
            provider=getattr(cfg, "provider", None),
            error_type=None,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            description=f"Loop over {len(items)} items",
        ),
    )
