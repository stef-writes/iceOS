"""Workflow execution service for the orchestrator."""
from __future__ import annotations
from typing import Any, Dict, Optional
from ice_orchestrator.workflow import Workflow

class WorkflowExecutionService:
    """Workflow execution service for the orchestrator runtime."""
    
    async def execute_workflow(
        self,
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
        # Create workflow from spec
        workflow = Workflow.from_dict(workflow_spec)
        
        # Execute workflow
        return await workflow.execute(context=inputs or {})
    
    async def execute_workflow_builder(
        self,
        builder: Any,  # WorkflowBuilder from SDK
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
        return await self.execute_workflow(spec, inputs)
 