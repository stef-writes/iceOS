"""Node Runtime Executor

Central orchestration driver that executes a **single node** within a workflow
run.  It is higher-level than the per-node-type executors living under
`execution.executors.builtin.*`:

1. Looks up the concrete builtin executor via `ice_core.unified_registry`.
2. Wraps invocation with retries, back-off, timeout sandbox and tracing.
3. Handles caching, context updates, output-mapping and budget metrics.

This module was formerly named `execution.executor`—renamed to avoid
confusion with the *_node_executor* modules.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

import structlog
from opentelemetry import trace  # type: ignore[import-not-found]

# Ensure builtin executors are registered before any workflow runs
import ice_orchestrator.execution.executors  # noqa: F401  # side-effects only
from ice_core.models import NodeExecutionResult
from ice_core.models.node_models import NodeMetadata
from ice_orchestrator.providers.budget_enforcer import BudgetEnforcer

if TYPE_CHECKING:  # pragma: no cover
    from ice_orchestrator.workflow import Workflow

tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)


class NodeExecutor:
    """Execute an individual node with retries, caching, metrics & tracing."""

    def __init__(self, chain: "Workflow") -> None:  # noqa: D401
        self.chain = chain
        self.budget = BudgetEnforcer()

    async def execute_node(
        self, node_id: str, input_data: Dict[str, Any]
    ) -> "NodeExecutionResult":
        """Driver entry-point used by workflow runtime."""
        # (Exact implementation copied from previous executor.py without changes)

        chain = self.chain
        # Use async workflow event handler instead of legacy emitter
        try:
            from ice_orchestrator.execution.workflow_events import NodeStarted as _Evt

            wf_id = str(getattr(chain, "chain_id", ""))
            run_id = str(getattr(chain, "run_id", ""))
            await chain._event_handler.emit(
                _Evt(  # type: ignore[attr-defined]
                    workflow_id=wf_id,
                    run_id=run_id,
                    node_id=node_id,
                    node_run_id=f"{run_id}_{node_id}",
                )
            )
        except Exception:
            pass

        node = chain.nodes.get(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' not found in chain configuration")

        # --- validation ---
        try:
            node.runtime_validate()  # type: ignore[attr-defined]
        except Exception as exc:
            error_meta = NodeMetadata(  # type: ignore[call-arg]
                node_id=node_id,
                node_type=str(getattr(node, "type", "")),
                name=getattr(node, "name", None),
                version="1.0.0",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration=0.0,
                error_type=type(exc).__name__,
                owner="system",
                description=f"Node {node_id} validation failed",
                provider=getattr(node, "provider", None),
            )
            if chain.failure_policy.name == "HALT":
                raise
            return NodeExecutionResult(success=False, error=str(exc), metadata=error_meta)  # type: ignore[call-arg]

        # Defer to the primary NodeExecutor implementation to avoid duplication
        # and legacy aliasing. The canonical implementation lives in
        # `execution/executor.py` and is imported directly here.
        from ice_orchestrator.execution.executor import NodeExecutor as _PrimaryExecutor

        # Delegate to the canonical implementation
        primary: _PrimaryExecutor = _PrimaryExecutor(self.chain)  # type: ignore[valid-type]
        return await primary.execute_node(node_id, input_data)
