"""Executor for parallel nodes."""

import asyncio
import contextlib
from datetime import datetime
from typing import Any, Dict, List

from ice_core.models import NodeExecutionResult, ParallelNodeConfig
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry

__all__ = ["parallel_node_executor"]


@register_node("parallel")
async def parallel_node_executor(  # noqa: D401, ANN001
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: Any,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:
    """Execute branches concurrently according to *cfg.wait_strategy*."""
    start_time = datetime.utcnow()

    try:
        # --------------------------------------------------------------
        # 1. Delegate to factory if registered -------------------------
        # --------------------------------------------------------------
        try:
            parallel_impl = registry.get_parallel_instance(
                getattr(cfg, "name", None) or cfg.id
            )
            out = await parallel_impl.execute(workflow=workflow, cfg=cfg, ctx=ctx)
            if isinstance(out, NodeExecutionResult):
                return out
            end_time = datetime.utcnow()
            return NodeExecutionResult(
                success=True,
                output=out,
                metadata=NodeMetadata(
                    node_id=getattr(cfg, "id", "parallel"),
                    node_type="parallel",
                    name=getattr(cfg, "name", None),
                    version="1.0.0",
                    owner="system",
                    provider=getattr(cfg, "provider", None),
                    error_type=None,
                    start_time=start_time,
                    end_time=end_time,
                    duration=(end_time - start_time).total_seconds(),
                    description="Parallel execution (factory)",
                ),
            )
        except KeyError:
            pass

        # --------------------------------------------------------------
        # 2. Normalise config -----------------------------------------
        # --------------------------------------------------------------
        if isinstance(cfg, ParallelNodeConfig):
            branches = cfg.branches
            wait_strategy = "all"
            merge_outputs = cfg.merge_outputs
        else:
            branches = getattr(cfg, "branches", [])
            wait_strategy = getattr(cfg, "wait_strategy", "all")
            merge_outputs = getattr(cfg, "merge_outputs", True)

        if not branches:
            raise ValueError(f"Parallel node {cfg.id} has no branches")

        # --------------------------------------------------------------
        # 2. Helper to execute a branch sequentially ------------------
        # --------------------------------------------------------------
        async def execute_branch(
            branch_nodes: List[Any], branch_idx: int
        ) -> Dict[str, Any]:
            branch_results: Dict[str, Any] = {}
            branch_ctx = {**ctx, "branch_index": branch_idx}

            for node in branch_nodes:
                if hasattr(workflow, "execute_node_config"):
                    node_result = await workflow.execute_node_config(
                        node,
                        branch_ctx,
                        parent_id=cfg.id,
                    )
                    branch_results[node.id] = (
                        node_result.output
                        if node_result.success
                        else {"error": node_result.error}
                    )
                    branch_ctx[node.id] = node_result.output
                else:
                    branch_results[node.id] = {
                        "status": "executed",
                        "branch": branch_idx,
                    }
            return branch_results

        # --------------------------------------------------------------
        # 3. Launch branches ------------------------------------------
        # --------------------------------------------------------------
        tasks: List[asyncio.Task[Dict[str, Any]]] = [
            asyncio.create_task(execute_branch(branch, idx))
            for idx, branch in enumerate(branches)
        ]
        completed_branches: List[int]

        if wait_strategy == "all":
            branch_results = await asyncio.gather(*tasks, return_exceptions=True)
            completed_branches = list(range(len(branches)))
        elif wait_strategy in {"any", "race"}:
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            branch_results = []
            completed_branches = []
            for idx, t in enumerate(tasks):
                if t in done:
                    try:
                        branch_results.append(await t)
                        completed_branches.append(idx)
                    except Exception as exc:  # pragma: no cover
                        branch_results.append({"error": str(exc)})
            for t in pending:
                t.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await t
        else:
            raise ValueError(f"Unknown wait strategy: {wait_strategy}")

        # --------------------------------------------------------------
        # 4. Result post-processing -----------------------------------
        # --------------------------------------------------------------
        processed: List[Dict[str, Any]] = []
        for idx, res in enumerate(branch_results):
            if isinstance(res, Exception):
                processed.append({"branch_error": str(res), "branch_index": idx})
            else:
                processed.append(res)  # type: ignore[arg-type]

        output: Dict[str, Any] = {
            "branch_results": processed,
            "completed_branches": completed_branches,
            "strategy": wait_strategy,
        }

        if merge_outputs and all(isinstance(r, dict) for r in processed):
            merged: Dict[str, Any] = {}
            for branch_result in processed:
                if "branch_error" in branch_result:
                    continue
                for nid, nout in branch_result.items():
                    if nid not in merged:
                        merged[nid] = nout
                    else:
                        if not isinstance(merged[nid], list):
                            merged[nid] = [merged[nid]]
                        merged[nid].append(nout)
            output["merged"] = merged

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
                description=f"Parallel execution: {len(branches)} branches",
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
                node_id=cfg.id,
                node_type=getattr(cfg, "type", "parallel"),
                name=getattr(cfg, "name", None),
                version="1.0.0",
                owner="system",
                error_type=type(exc).__name__,
                provider=getattr(cfg, "provider", None),
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                description=f"Parallel execution failed: {len(getattr(cfg, 'branches', []))} branches",
            ),
            execution_time=duration,
        )
