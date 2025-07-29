from __future__ import annotations

"""Light-weight multi-workflow coordinator.

This module provides the **minimum viable implementation** for executing a group
of iceOS workflows described in a single YAML/JSON manifest ("network file").
It deliberately avoids introducing a heavy *NetworkSpec* schema or a new
execution engine – it simply loads existing ``Workflow`` objects and runs them
in the required order.

Key capabilities implemented now:

1. Parse a manifest with the following structure::

    api_version: network.v0
    name: my_network
    global:                    # optional – injected into each workflow's context
      budget_usd: 5
      memory_backend: redis://localhost:6379/3
    workflows:
      - id: etl_job            # optional identifier for dependency graph
        ref: path.to.module:create_workflow  # import path (``module:attr``)
      - id: training_job
        ref: another.mod:build_training
        after: etl_job         # simple dependency – run after *etl_job*

2. Resolve each ``ref`` into a concrete ``Workflow`` instance using dynamic
   import (allowed at this layer by repo rule **18**).
3. Respect ``after`` dependencies and execute workflows sequentially once their
   prerequisites complete (no parallelism yet – KISS for MVP).
4. Inject the ``global`` section into the *initial_context* of every workflow.
5. Expose a synchronous ``run()`` helper and an async ``execute()`` coroutine.

Future work (not in this MVP):
– Cron / schedule handling
– Parallel execution of independent workflows
– Rich telemetry aggregation & cost enforcement
– Promotion of the manifest into a strict ``NetworkSpec`` Pydantic model
– CLI wrapper
"""

import asyncio
import importlib
import inspect
import copy
import logging
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional

import yaml  # PyYAML is already a transitive dependency
from pydantic import BaseModel, Field, ValidationError

# Structured logging
logger = logging.getLogger(__name__)

from ice_sdk.services import ServiceLocator

# ---------------------------------------------------------------------------
# Manifest models – deliberately forgiving (extra allowed)                   
# ---------------------------------------------------------------------------

class WorkflowEntry(BaseModel):
    """Entry describing one workflow inside the network manifest."""

    ref: str = Field(..., description="Python import path (module[:attr]) returning a Workflow")
    id: Optional[str] = Field(None, description="Optional unique identifier for dependencies")
    after: Optional[str] = Field(
        None,
        description="ID of another workflow that must finish before this one starts",
    )

    model_config = dict(extra="allow")  # allow schedule, deploy_target, etc.

class NetworkManifest(BaseModel):
    api_version: str = Field("network.v0", description="Manifest version")
    name: str
    global_config: Dict[str, Any] = Field(default_factory=dict, alias="global")
    workflows: List[WorkflowEntry]

    model_config = dict(populate_by_name=True, extra="allow")

# ---------------------------------------------------------------------------
# Coordinator                                                                 
# ---------------------------------------------------------------------------


class NetworkCoordinator:
    """Load a manifest file and execute the referenced workflows in order."""

    def __init__(self, manifest: NetworkManifest, *, max_concurrent: int = 5):
        self.manifest = manifest
        self._workflow_class = ServiceLocator.get("workflow_proto")
        if self._workflow_class is None:
            raise RuntimeError(
                "Workflow implementation not registered – did you call initialize_orchestrator()?"
            )

        # Concurrency guard for parallel workflow execution
        self._sem = asyncio.Semaphore(max_concurrent)

    # ------------------------------------------------------------------
    # Public helpers                                                     
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str | Path) -> "NetworkCoordinator":
        """Parse *path* (YAML or JSON) into :class:`NetworkCoordinator`."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        data = yaml.safe_load(path.read_text())
        try:
            manifest = NetworkManifest.model_validate(data)
        except ValidationError as e:
            raise ValueError(f"Invalid network manifest {path}: {e}") from e
        return cls(manifest)

    def run(self) -> Dict[str, Any]:  # synchronous wrapper
        """Convenience wrapper around ``asyncio.run(self.execute())``."""
        return asyncio.run(self.execute())

    async def execute(self) -> Dict[str, Any]:
        """Execute all workflows respecting *after* dependencies **in parallel** when possible.

        Returns a mapping ``{workflow_id_or_ref: execution_result}``.
        """
        batches = self._resolve_execution_batches()
        results: Dict[str, Any] = {}

        for batch in batches:
            # Run workflows in the current *batch* concurrently
            async def _run(entry: WorkflowEntry):
                async with self._sem:
                    try:
                        wf = self._prepare_workflow(entry)
                        return await wf.execute()
                    except Exception as exc:
                        logger.error(
                            "Workflow '%s' failed: %s", entry.id or entry.ref, exc, exc_info=True
                        )
                        return exc

            batch_results = await asyncio.gather(
                *[_run(e) for e in batch], return_exceptions=True
            )

            for entry, res in zip(batch, batch_results):
                # Normalise exception into failure result for uniformity
                if isinstance(res, Exception):
                    from datetime import datetime
                    from ice_core.models.node_models import NodeMetadata, NodeExecutionResult

                    results[entry.id or entry.ref] = NodeExecutionResult(  # type: ignore[call-arg]
                        success=False,
                        error=str(res),
                        metadata=NodeMetadata(  # type: ignore[call-arg]
                            node_id=entry.id or entry.ref,
                            node_type="workflow",
                            name=entry.id or entry.ref,
                            start_time=datetime.utcnow(),
                            end_time=datetime.utcnow(),
                            duration=0.0,
                            error_type=type(res).__name__,
                        ),
                    )
                else:
                    results[entry.id or entry.ref] = res

        return results

    # ------------------------------------------------------------------
    # Optional cron-style scheduled execution (long-running)             
    # ------------------------------------------------------------------

    async def execute_scheduled(self, *, loop_forever: bool = True) -> None:  # pragma: no cover
        """Execute workflows according to their ``schedule`` field (cron expr).

        This helper blocks (optionally forever) and triggers workflows when
        their cron expression is due.  Requires **croniter**.  Workflows
        without ``schedule`` are executed immediately once at startup.
        """

        try:
            from croniter import croniter  # type: ignore
        except ImportError as e:  # pragma: no cover – optional dep
            raise RuntimeError("croniter is required for scheduled execution – install with 'pip install croniter'") from e

        import datetime
        import heapq

        # Pre-compute next run times ------------------------------------------------
        now = datetime.datetime.now()
        schedule_heap: list[tuple[float, WorkflowEntry]] = []  # timestamp, entry
        unscheduled: list[WorkflowEntry] = []

        for entry in self.manifest.workflows:
            schedule = getattr(entry, "schedule", None)
            if schedule:
                itr = croniter(schedule, now)
                nxt = itr.get_next(datetime.datetime).timestamp()
                heapq.heappush(schedule_heap, (nxt, entry))
            else:
                unscheduled.append(entry)

        # Execute non-scheduled ones first -----------------------------------------
        if unscheduled:
            await self.execute()

        # Main scheduling loop -------------------------------------------------------
        while schedule_heap:
            nxt_ts, entry = heapq.heappop(schedule_heap)
            sleep_for = max(0, nxt_ts - datetime.datetime.now().timestamp())
            await asyncio.sleep(sleep_for)
            # Execute the single workflow (ignoring deps since schedule is explicit)
            await self._load_workflow(entry.ref).execute()

            if loop_forever:
                itr = croniter(getattr(entry, "schedule"), datetime.datetime.now())
                nxt2 = itr.get_next(datetime.datetime).timestamp()
                heapq.heappush(schedule_heap, (nxt2, entry))

    # ------------------------------------------------------------------
    # Internal helpers                                                   
    # ------------------------------------------------------------------

    def _resolve_execution_order(self) -> List[WorkflowEntry]:
        given = {w.id or f"idx_{i}": w for i, w in enumerate(self.manifest.workflows)}
        ordered: List[WorkflowEntry] = []
        visited: set[str] = set()

        def visit(w: WorkflowEntry) -> None:
            key = w.id or w.ref
            if key in visited:
                return
            if w.after:
                if w.after not in given:
                    raise ValueError(f"Unknown dependency '{w.after}' in workflow '{key}'")
                visit(given[w.after])
            ordered.append(w)
            visited.add(key)

        for w in self.manifest.workflows:
            visit(w)
        return ordered

    def _resolve_execution_batches(self) -> List[List[WorkflowEntry]]:
        """Return execution batches: each inner list can run in parallel."""
        order = self._resolve_execution_order()
        # Build mapping for quick lookup of dependencies
        id_map = {e.id or e.ref: e for e in order}
        dep_counts = {e: 0 for e in order}
        for e in order:
            if e.after:
                dep_counts[e] += 1
        # Kahn's algorithm to compute levels
        ready = [e for e, c in dep_counts.items() if c == 0]
        batches: list[list[WorkflowEntry]] = []
        while ready:
            batches.append(ready)
            next_ready: list[WorkflowEntry] = []
            for e in ready:
                for other in order:
                    if other.after == (e.id or e.ref):
                        dep_counts[other] -= 1
                        if dep_counts[other] == 0:
                            next_ready.append(other)
            ready = next_ready
        return batches

    # --------------------------------------------------------------
    # Dynamic workflow loader                                       
    # --------------------------------------------------------------
    def _load_workflow(self, ref: str):  # noqa: ANN401 – Any Workflow subtype
        """Import *ref* and return a Workflow instance.

        ``ref`` can be either ``module`` or ``module:attr``. When *attr* is
        provided and resolves to a *callable*, it will be called (without
        arguments) to obtain the workflow object.
        """
        try:
            if ":" in ref:
                module_path, attr_name = ref.split(":", 1)
            else:
                module_path, attr_name = ref, None

            try:
                module: ModuleType = importlib.import_module(module_path)
            except ModuleNotFoundError as exc:
                raise ValueError(
                    f"Module '{module_path}' in workflow ref '{ref}' not found. "
                    "Ensure the module is installed and PYTHONPATH is correct."
                ) from exc

            obj = module
            if attr_name:
                try:
                    obj = getattr(module, attr_name)
                except AttributeError as exc:
                    raise ValueError(
                        f"Attribute '{attr_name}' not found in module '{module_path}' for ref '{ref}'."
                    ) from exc

                if inspect.isfunction(obj) or inspect.isclass(obj):
                    try:
                        obj = obj()  # type: ignore[call-arg]
                    except TypeError as exc:
                        raise ValueError(
                            f"Factory '{attr_name}' in module '{module_path}' requires arguments. "
                            "Provide a zero-argument factory or wrap in lambda."
                        ) from exc

            if not isinstance(obj, self._workflow_class):
                raise TypeError(
                    f"Resolved object for '{ref}' is not a Workflow instance (got {type(obj).__name__})."
                )

            return obj
        except Exception as exc:
            # Re-raise with ref context for easier debugging
            raise RuntimeError(f"Failed to load workflow '{ref}': {exc}") from exc

    # ------------------------------------------------------------------
    # Helpers                                                            
    # ------------------------------------------------------------------

    def _prepare_workflow(self, entry: WorkflowEntry):
        """Clone workflow and inject global context safely."""
        wf = self._load_workflow(entry.ref)
        # Deep copy to avoid mutating shared workflows loaded via import
        wf_clone = copy.deepcopy(wf)
        if hasattr(wf_clone, "initial_context"):
            try:
                existing = getattr(wf_clone, "initial_context", {}) or {}
                wf_clone.initial_context = {**existing, **self.manifest.global_config}
            except Exception as exc:  # pragma: no cover – defensive
                logger.warning("Failed to inject global context into workflow '%s': %s", entry.ref, exc)
        return wf_clone 