from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from app.chains.orchestration.workflow_execution_context import WorkflowExecutionContext
from app.models.node_models import NodeConfig, NodeExecutionResult

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
        context_manager: Optional[Any] = None,
        callbacks: Optional[List[Any]] = None,
        max_parallel: int = 5,
        persist_intermediate_outputs: bool = True,
        tool_service: Optional[Any] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[WorkflowExecutionContext] = None,
        failure_policy: FailurePolicy = FailurePolicy.CONTINUE_POSSIBLE,
    ):
        self.nodes = {node.id: node for node in nodes}
        self.name = name or "script_chain"
        self.context_manager = context_manager
        self.max_parallel = max_parallel
        self.persist_intermediate_outputs = persist_intermediate_outputs
        self.tool_service = tool_service
        self.initial_context = initial_context or {}
        self.callbacks = callbacks or []
        self.workflow_context = workflow_context or WorkflowExecutionContext()
        self.failure_policy = failure_policy

    @abstractmethod
    async def execute(self) -> NodeExecutionResult:
        """
        Execute the workflow and return a NodeExecutionResult.
        Must be implemented by subclasses.
        """
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
