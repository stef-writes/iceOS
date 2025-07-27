"""Real workflow service implementation for MCP.

This service implements the IWorkflowService protocol and provides the actual
workflow execution capabilities that MCP endpoints need.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import structlog

from ice_core.models import NodeConfig
from ice_core.services.contracts import IWorkflowService
from ice_orchestrator.workflow import Workflow
from ice_orchestrator.context import GraphContextManager

# Tools are accessed via unified registry, not imported directly

logger = structlog.get_logger(__name__)

class WorkflowService(IWorkflowService):
    """Real workflow service implementation.

    This service provides the actual workflow execution capabilities that
    MCP endpoints need. It uses the real Workflow class for execution
    and returns structured results with metrics.
    """

    def __init__(self):
        """Initialize the workflow service."""
        # Use context manager from ServiceLocator if available, otherwise create new one
        from ice_sdk.services.locator import ServiceLocator
        self._context_manager = ServiceLocator.get("context_manager")
        if self._context_manager is None:
            self._context_manager = GraphContextManager()
        
        # Tools are auto-registered via @tool decorator when SDK is initialized
        # No need to manually import and register them here

    async def execute(
        self,
        nodes: list[Any],  # NodeConfig-compatible payloads
        name: str,
        max_parallel: int = 5,
        *,
        run_id: str | None = None,
        event_emitter: Any | None = None,
    ) -> Dict[str, Any]:
        """Execute a workflow with the given nodes.

        Args:
            nodes: List of NodeConfig objects or compatible dicts
            name: Name of the workflow
            max_parallel: Maximum parallel execution (default: 5)

        Returns:
            Dictionary containing execution results with metrics
        """
        try:
            # Convert dict nodes to NodeConfig objects if needed
            node_configs = []
            for node in nodes:
                # Accept both raw dicts and already-built NodeConfig (or any
                # subclass thereof).  We avoid ``isinstance(..., NodeConfig)``
                # because ``NodeConfig`` is a *typing.Annotated* alias which
                # raises ``TypeError`` when used with ``isinstance``.
                if isinstance(node, dict):
                    node_configs.append(NodeConfig(**node))
                else:
                    # Assume it's a valid *BaseNodeConfig* or compatible
                    # object; Pydantic validation inside ``Workflow`` will
                    # surface any structural issues later.
                    node_configs.append(node)  # type: ignore[arg-type]

            # Create event emitter closure if provided
            def _emit(event_name: str, payload: Dict[str, Any]) -> None:
                if event_emitter:
                    event_emitter(event_name, payload)

            workflow = Workflow(
                nodes=node_configs,
                name=name,
                chain_id=run_id,
                context_manager=self._context_manager,
            )

            # Validate workflow before execution
            if hasattr(workflow, "validate"):
                workflow.validate()

            start_time = datetime.utcnow()

            # Execute the workflow
            result = await workflow.execute()

            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()

            result_dict = {
                "success": True,
                "start_time": start_time,
                "end_time": end_time,
                "execution_time": execution_time,
                "output": result,
                "error": None,
                "metrics": {
                    "total_nodes": len(node_configs),
                    "max_parallel": max_parallel,
                    "actual_parallel": min(len(node_configs), max_parallel),
                },
            }
            if run_id is not None:
                result_dict["run_id"] = run_id  # non-breaking extra field

            return result_dict

        except Exception as exc:
            logger.error(
                "Workflow execution failed", error=str(exc), workflow_name=name
            )
            error_dict = {
                "success": False,
                "start_time": datetime.utcnow(),
                "end_time": datetime.utcnow(),
                "execution_time": 0.0,
                "output": {},
                "error": str(exc),
                "metrics": {
                    "total_nodes": len(nodes) if nodes else 0,
                    "max_parallel": max_parallel,
                    "actual_parallel": 0,
                },
            }
            if run_id is not None:
                error_dict["run_id"] = run_id

            return error_dict

    async def create_partial_blueprint(self) -> str:
        """Create a new partial blueprint for incremental building."""
        import uuid
        blueprint_id = f"blueprint_{uuid.uuid4().hex[:8]}"
        # In a real implementation, this would store the blueprint
        # For now, just return the ID
        return blueprint_id
