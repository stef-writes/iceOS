from __future__ import annotations

# ruff: noqa: E402

"""Abstract orchestration base helpers (moved from *ice_sdk.orchestrator*).

No functional changes – path only.  All downstream imports should use
``ice_orchestrator.base_workflow``.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from typing import cast as _cast
from uuid import uuid4

from ice_core.models import NodeConfig, NodeExecutionResult
from ice_orchestrator.workflow_execution_context import WorkflowExecutionContext
from ice_sdk.context import GraphContextManager
from ice_sdk.context.manager import GraphContext
from ice_sdk.services import ServiceLocator
from ice_sdk.tools.base import ToolBase

class FailurePolicy(str, Enum):
    """Strategies controlling how the chain proceeds after node failures."""

    HALT = "halt_on_first_error"
    CONTINUE_POSSIBLE = "continue_if_possible"
    ALWAYS = "always_continue"

class BaseWorkflow(ABC):
    """Abstract base class for all Workflow (formerly ScriptChain) types."""

    def __init__(
        self,
        nodes: List[NodeConfig],
        name: Optional[str] = None,
        context_manager: Optional[GraphContextManager] = None,
        callbacks: Optional[List[Any]] = None,
        max_parallel: int = 5,
        persist_intermediate_outputs: bool = True,
        tools: Optional[List[ToolBase]] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[WorkflowExecutionContext] = None,
        failure_policy: FailurePolicy = FailurePolicy.CONTINUE_POSSIBLE,
        *,
        run_id: Optional[str] = None,
        event_emitter: Callable[[str, Dict[str, Any]], None] | None = None,
        session_id: Optional[str] = None,
        use_cache: bool = True,
    ):
        # Identifiers ----------------------------------------------------
        self.run_id = run_id
        self.session_id = session_id or uuid4().hex
        # Event emitter --------------------------------------------------
        self._emit_event = event_emitter
        self.use_cache = use_cache

        self.nodes = {node.id: node for node in nodes}
        self.name = name or "workflow"

        if context_manager is None:
            try:
                context_manager = ServiceLocator.get("context_manager")
            except KeyError:
                context_manager = GraphContextManager()
                ServiceLocator.register("context_manager", context_manager)

        self.context_manager = _cast(GraphContextManager, context_manager)
        self.max_parallel = max_parallel
        self.persist_intermediate_outputs = persist_intermediate_outputs
        self.callbacks = callbacks or []
        self.workflow_context = workflow_context or WorkflowExecutionContext()
        self.failure_policy = failure_policy

        if tools:
            for tool in tools:
                self.context_manager.register_tool(tool)

        context_metadata = initial_context or {}
        self.context_manager.set_context(
            GraphContext(
                session_id=self.session_id,
                metadata=context_metadata,
                execution_id=f"{self.session_id}_{datetime.utcnow().isoformat()}",
            )
        )

    # ------------------------------------------------------------------ abstract API
    @abstractmethod
    async def execute(self) -> NodeExecutionResult:
        pass

    @abstractmethod
    def get_node_dependencies(self, node_id: str) -> List[str]:
        pass

    @abstractmethod
    def get_node_dependents(self, node_id: str) -> List[str]:
        pass

    @abstractmethod
    def get_node_level(self, node_id: str) -> int:
        pass

    @abstractmethod
    def get_level_nodes(self, level: int) -> List[str]:
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def execute_node(
        self, node_id: str, input_data: Dict[str, Any]
    ) -> NodeExecutionResult:
        pass
