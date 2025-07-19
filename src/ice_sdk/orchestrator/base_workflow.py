"""Abstract orchestration base helpers.

This module defines the foundational ABC for workflow execution.  New code
should import `BaseWorkflow` – an alias of `BaseScriptChain` kept for
compatibility while we migrate away from the *ScriptChain* terminology.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from typing import cast as _cast
from uuid import uuid4

from ice_sdk.context import GraphContextManager
from ice_sdk.context.manager import GraphContext
from ice_sdk.models.node_models import NodeConfig, NodeExecutionResult
from ice_sdk.services import ServiceLocator
from ice_sdk.skills.base import SkillBase  # migrated from BaseTool

from .workflow_execution_context import WorkflowExecutionContext

# ---------------------------------------------------------------------------
# Failure handling strategy --------------------------------------------------
# ---------------------------------------------------------------------------


class FailurePolicy(str, Enum):
    """Strategies controlling how the chain proceeds after node failures."""

    HALT = "halt_on_first_error"
    CONTINUE_POSSIBLE = "continue_if_possible"
    ALWAYS = "always_continue"


class BaseScriptChain(ABC):
    """
    Abstract base class for all ScriptChain types.
    Defines the common interface and shared logic for workflow orchestration.
    """

    def __init__(
        self,
        nodes: List[NodeConfig],
        name: Optional[str] = None,
        context_manager: Optional[GraphContextManager] = None,
        callbacks: Optional[List[Any]] = None,
        max_parallel: int = 5,
        persist_intermediate_outputs: bool = True,
        tools: Optional[List[SkillBase]] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[WorkflowExecutionContext] = None,
        failure_policy: FailurePolicy = FailurePolicy.CONTINUE_POSSIBLE,
        *,
        session_id: Optional[str] = None,
        use_cache: bool = True,
    ):
        """Initialize script chain.

        Args:
            nodes: List of node configurations
            name: Chain name
            context_manager: Context manager
            callbacks: List of callbacks
            max_parallel: Maximum parallel executions
            persist_intermediate_outputs: Whether to persist outputs
            tools: List of tools available to nodes
            initial_context: Initial execution context
            workflow_context: Workflow execution context
            failure_policy: Failure handling policy
            session_id: Optional session ID
            use_cache: Whether to use cache
        """
        self.session_id = session_id or uuid4().hex
        self.use_cache = use_cache

        self.nodes = {node.id: node for node in nodes}
        self.name = name or "script_chain"
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

        # Register tools
        if tools:
            for tool in tools:
                self.context_manager.register_tool(tool)

        # Set initial context – always create a workflow-scoped context
        context_metadata = initial_context or {}
        self.context_manager.set_context(
            GraphContext(
                session_id=self.session_id,
                metadata=context_metadata,
                execution_id=f"{self.session_id}_{datetime.utcnow().isoformat()}",
            )
        )

    @abstractmethod
    async def execute(self) -> NodeExecutionResult:
        """Execute the workflow and return a NodeExecutionResult."""
        pass

    @abstractmethod
    def get_node_dependencies(self, node_id: str) -> List[str]:
        """Get dependencies for a node."""
        pass

    @abstractmethod
    def get_node_dependents(self, node_id: str) -> List[str]:
        """Get dependents for a node."""
        pass

    @abstractmethod
    def get_node_level(self, node_id: str) -> int:
        """Get execution level for a node."""
        pass

    @abstractmethod
    def get_level_nodes(self, level: int) -> List[str]:
        """Get nodes at a specific level."""
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics."""
        pass

    @abstractmethod
    async def execute_node(
        self, node_id: str, input_data: Dict[str, Any]
    ) -> NodeExecutionResult:
        """Execute a single node and return its :class:`NodeExecutionResult`.  Must be
        implemented by concrete subclasses (e.g. :class:`ScriptChain`)."""


# ---------------------------------------------------------------------------
# Preferred naming shim ------------------------------------------------------
# ---------------------------------------------------------------------------
BaseWorkflow = BaseScriptChain  # type: ignore

# Flag legacy name as deprecated in the docstring so linters surface it
BaseScriptChain.__doc__ = (
    BaseScriptChain.__doc__ or ""
) + "\n\nDeprecated alias: use BaseWorkflow instead."
