"""Workflow execution service facade for SDK users."""
from __future__ import annotations
from typing import Any, Dict, Optional
from ice_sdk.services.locator import ServiceLocator

class WorkflowExecutionService:
    """Facade for workflow execution without importing orchestrator directly."""
    
    @staticmethod
    async def execute_workflow(
        workflow_spec: Dict[str, Any],
        inputs: Optional[Dict[str, Any]] = None,
        context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute a workflow from its specification.
        
        Args:
            workflow_spec: Workflow specification (from WorkflowBuilder.build())
            inputs: Initial inputs for the workflow
            context: Optional execution context
            
        Returns:
            Workflow execution results
        """
        # Get workflow service from ServiceLocator
        workflow_service = ServiceLocator.get("workflow_service")
        if not workflow_service:
            raise RuntimeError(
                "Workflow service not registered. Ensure ice_orchestrator is initialized."
            )
        
        # Execute through the service
        return await workflow_service.execute_dict(workflow_spec, inputs or {})
    
    @staticmethod
    async def execute_workflow_builder(
        builder: "WorkflowBuilder",
        inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a workflow directly from a builder.
        
        Args:
            builder: WorkflowBuilder instance
            inputs: Initial inputs for the workflow
            
        Returns:
            Workflow execution results
        """
        spec = builder.build()
        return await WorkflowExecutionService.execute_workflow(spec, inputs)
    
    @staticmethod
    def register_workflow(name: str, spec: Dict[str, Any]) -> None:
        """Register a workflow spec for later execution by name.
        
        Args:
            name: Unique workflow name
            spec: Workflow specification
        """
        workflow_service = ServiceLocator.get("workflow_service")
        if workflow_service:
            workflow_service.register_spec(name, spec) 