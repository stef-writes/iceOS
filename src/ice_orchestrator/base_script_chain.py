from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ice_orchestrator.workflow_execution_context import WorkflowExecutionContext
from ice_sdk.context.manager import GraphContext, GraphContextManager
from ice_sdk.models.node_models import NodeConfig, NodeExecutionResult
from ice_sdk.tools.base import BaseTool

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
        tools: Optional[List[BaseTool]] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[WorkflowExecutionContext] = None,
        failure_policy: FailurePolicy = FailurePolicy.CONTINUE_POSSIBLE,
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
        """
        self.nodes = {node.id: node for node in nodes}
        self.name = name or "script_chain"
        self.context_manager = context_manager or GraphContextManager()
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
                session_id=self.name,
                metadata=context_metadata,
                execution_id=f"{self.name}_{datetime.utcnow().isoformat()}",
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

    async def execute_node(self, node_id: str, input_data: Dict[str, Any]) -> NodeExecutionResult:
        """Execute a single node.
        
        Args:
            node_id: Node ID
            input_data: Input data
        """
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node '{node_id}' not found")
            
        # Update node context
        self.context_manager.update_node_context(
            node_id=node_id,
            content=input_data,
            execution_id=self.context_manager.get_context().execution_id
        )
        
        # Execute node
        try:
            result = await node.execute(input_data)
            
            # Persist output if configured
            if self.persist_intermediate_outputs:
                self.context_manager.update_node_context(
                    node_id=node_id,
                    content=result.output,
                    execution_id=self.context_manager.get_context().execution_id
                )
                
            return result
            
        except Exception as e:
            if self.failure_policy == FailurePolicy.HALT:
                raise
            elif self.failure_policy == FailurePolicy.CONTINUE_POSSIBLE:
                # Check if dependents can still execute
                dependents = self.get_node_dependents(node_id)
                if not dependents:
                    return NodeExecutionResult(
                        success=False,
                        error=str(e),
                        output=None
                    )
                # Continue execution
                return NodeExecutionResult(
                    success=False,
                    error=str(e),
                    output=None
                )
            else:  # ALWAYS
                return NodeExecutionResult(
                    success=False,
                    error=str(e),
                    output=None
                )
