"""iceOS Orchestrator - Runtime Execution Engine.

The orchestrator layer handles all runtime execution including:
- Workflow execution
- Tool execution 
- Agent runtime
- Memory management
- LLM services
- Context management
"""

from ice_orchestrator.base_workflow import BaseWorkflow, FailurePolicy
from ice_orchestrator.services.workflow_service import WorkflowService

__all__ = ["BaseWorkflow", "FailurePolicy", "WorkflowService", "initialize_orchestrator"]


def initialize_orchestrator() -> None:
    """Initialize the orchestrator layer with all runtime services.
    
    This function registers all runtime services that the SDK and API layers
    can access via ServiceLocator.
    """
    # Register context manager first – other services depend on it
    import os
    from pathlib import Path

    from ice_core.llm.service import LLMService
    from ice_core.services import ServiceLocator
    from ice_orchestrator.context import GraphContextManager
    from ice_orchestrator.services.network_coordinator import NetworkCoordinator
    from ice_orchestrator.services.task_manager import NetworkTaskManager
    from ice_orchestrator.services.tool_execution_service import ToolExecutionService
    from ice_orchestrator.services.workflow_execution_service import (
        WorkflowExecutionService,
    )
    from ice_orchestrator.services.workflow_service import WorkflowService
    from ice_orchestrator.workflow import Workflow
    project_root = Path(os.getcwd())
    ServiceLocator.register("context_manager", GraphContextManager(project_root=project_root))
    
    # Register core services
    ServiceLocator.register("workflow_proto", Workflow)
    ServiceLocator.register("workflow_service", WorkflowService())
    ServiceLocator.register("workflow_execution_service", WorkflowExecutionService())
    ServiceLocator.register("tool_execution_service", ToolExecutionService())
    ServiceLocator.register("llm_service", LLMService())
    ServiceLocator.register("llm_service_impl", LLMService())  # For SDK adapter compatibility
    # Register network coordinator class for SDK-level NetworkService
    ServiceLocator.register("network_coordinator_cls", NetworkCoordinator)
    ServiceLocator.register("network_task_manager", NetworkTaskManager())
    
    # Register tool service wrapper
    from ice_core.services.tool_service import ToolService
    ServiceLocator.register("tool_service", ToolService())
    
    # Import executor modules to register them with the execution system
    import ice_orchestrator.execution.executors  # noqa: F401
    import ice_orchestrator.execution.executors.unified  # noqa: F401

    # ------------------------------------------------------------------
    # Built-in tools will be loaded via toolkits once implemented.
    # ------------------------------------------------------------------
    # (No built-in tool packages shipped yet – placeholder for future.)
