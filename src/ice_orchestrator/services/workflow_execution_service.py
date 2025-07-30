"""Workflow execution service for the orchestrator."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from ice_core.models.mcp import NodeSpec
from ice_core.utils.node_conversion import convert_node_specs
from ice_orchestrator.workflow import Workflow

class WorkflowExecutionService:
    """Workflow execution service for the orchestrator runtime.
    
    This service provides two clear entry points:
    1. execute_blueprint - for MCP layer blueprints (List[NodeSpec])
    2. execute_workflow - for ready Workflow instances
    """
    
    async def execute_blueprint(
        self,
        node_specs: List[NodeSpec],
        *,
        inputs: Optional[Dict[str, Any]] = None,
        max_parallel: int = 5,
        name: str = "blueprint_run"
    ) -> Dict[str, Any]:
        """Execute a workflow from MCP blueprint specification.
        
        Args:
            node_specs: List of NodeSpec objects from MCP layer
            inputs: Initial inputs for the workflow
            max_parallel: Maximum parallel execution
            name: Workflow name
            
        Returns:
            Workflow execution results
        """
        # Convert NodeSpec to NodeConfig
        node_configs = convert_node_specs(node_specs)
        
        # Create workflow with proper initial context
        workflow = Workflow(
            nodes=node_configs,
            name=name,
            max_parallel=max_parallel,
            initial_context={"inputs": inputs} if inputs else None
        )
        
        # Execute workflow
        return await workflow.execute()
    
    async def execute_workflow(
        self,
        workflow: Workflow,
        *,
        inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a ready Workflow instance.
        
        Args:
            workflow: Workflow instance to execute
            inputs: Initial inputs to inject into workflow context
            
        Returns:
            Workflow execution results
        """
        # Inject inputs into workflow context if provided
        if inputs:
            ctx = workflow.context_manager.get_context(session_id="run")
            if ctx:
                ctx.metadata["inputs"] = inputs
        
        # Execute workflow
        return await workflow.execute()
    
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
        # Builder.build() returns a Blueprint, so use execute_blueprint
        blueprint = builder.build()
        return await self.execute_blueprint(
            blueprint.nodes, 
            inputs=inputs, 
            name=builder.name
        )
 