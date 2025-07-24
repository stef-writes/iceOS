"""Ice Orchestrator package.

This package provides workflow orchestration capabilities for iceOS.
"""

from ice_orchestrator.base_workflow import BaseWorkflow, FailurePolicy
from ice_orchestrator.workflow_execution_context import WorkflowExecutionContext
from ice_orchestrator.services.workflow_service import WorkflowService
from ice_sdk.services import ServiceLocator

# New exports
from .graph.dependency_graph import DependencyGraph
from .workflow import Workflow

def initialize_orchestrator() -> None:
    """Initialize orchestrator services and register them with ServiceLocator.
    
    This function should be called once during application startup to register
    all orchestrator services that the SDK and API layers need.
    """
    # Register workflow service for MCP/API usage
    ServiceLocator.register("workflow_service", WorkflowService())
    
    # Register workflow prototype for SDK usage
    ServiceLocator.register("workflow_proto", Workflow)

__all__ = [
    "BaseWorkflow",
    "FailurePolicy",
    "WorkflowExecutionContext", 
    "WorkflowService",
    "DependencyGraph",
    "Workflow",
    "initialize_orchestrator",
]
