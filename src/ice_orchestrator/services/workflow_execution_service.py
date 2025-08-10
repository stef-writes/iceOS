"""Workflow execution service for the orchestrator."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ice_core.metrics import EXEC_COMPLETED, EXEC_STARTED
from ice_core.models.mcp import NodeSpec
from ice_core.models.node_models import NodeExecutionResult
from ice_core.utils.node_conversion import convert_node_specs
from ice_orchestrator.workflow import Workflow

# Importing registry solely for side-effects would be unused; remove to satisfy linter


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
        name: str = "blueprint_run",
    ) -> NodeExecutionResult:
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

        # Ensure first-party generated tools are registered explicitly
        try:
            from ice_orchestrator.plugins import load_first_party_tools

            load_first_party_tools()
        except Exception:
            pass

        # Create workflow with proper initial context
        # Merge provided inputs at the top level and also under the "inputs" key
        # so prompts can access placeholders like {topic} without nesting.
        initial_ctx = None
        if inputs:
            initial_ctx = {**inputs, "inputs": inputs}
        workflow = Workflow(
            nodes=node_configs,
            name=name,
            max_parallel=max_parallel,
            initial_context=initial_ctx,
        )

        # Execute workflow
        EXEC_STARTED.inc()
        try:
            result = await workflow.execute()
            EXEC_COMPLETED.inc()
            return result
        except Exception:
            EXEC_COMPLETED.inc()
            raise

    async def execute_workflow(
        self, workflow: Workflow, *, inputs: Optional[Dict[str, Any]] = None
    ) -> NodeExecutionResult:
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
                # Expose inputs both at top-level and nested under "inputs"
                ctx.metadata.update(inputs)
                ctx.metadata["inputs"] = inputs

        # Execute workflow
        EXEC_STARTED.inc()
        try:
            result = await workflow.execute()
            EXEC_COMPLETED.inc()
            return result
        except Exception:
            EXEC_COMPLETED.inc()
            raise

    async def execute_workflow_builder(
        self,
        builder: Any,  # WorkflowBuilder
        inputs: Optional[Dict[str, Any]] = None,
    ) -> NodeExecutionResult:
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
            blueprint.nodes, inputs=inputs, name=builder.name
        )
