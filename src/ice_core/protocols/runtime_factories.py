"""Runtime factory and service protocols.

These lightweight ``Protocol`` definitions allow the compile-time layers
(*ice_core*, *ice_builder*, *ice_api*) to reference runtime
implementations (*ice_orchestrator*) **without** importing them directly.

The orchestrator layer must set concrete implementations at process
start-up::

    import ice_core.runtime as rt
    from ice_orchestrator.workflow import Workflow
    from ice_orchestrator.services.network_coordinator import NetworkCoordinator
    from ice_orchestrator.services.tool_execution_service import ToolExecutionService

    rt.workflow_factory = Workflow  # callable/class
    rt.network_coordinator_factory = NetworkCoordinator  # class with ``from_file``
    rt.tool_execution_service = ToolExecutionService()

Callers then pick these up explicitly via ``ice_core.runtime``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Protocol, runtime_checkable

__all__ = [
    "WorkflowFactory",
    "NetworkCoordinatorFactory",
    "ToolExecutionServiceProtocol",
]


@runtime_checkable
class WorkflowFactory(Protocol):
    """Factory for creating *Workflow* runtime objects."""

    def __call__(self, *, name: str, nodes: list[Any]) -> Any:  # noqa: D401
        ...


@runtime_checkable
class NetworkCoordinatorFactory(Protocol):
    """Factory for building a *NetworkCoordinator* from manifest file."""

    @classmethod
    def from_file(cls, path: Path) -> Any:  # noqa: D401
        ...


@runtime_checkable
class ToolExecutionServiceProtocol(Protocol):
    """Required subset of the ToolExecutionService public API."""

    async def execute_tool(
        self, tool_name: str, inputs: Dict[str, Any], context: Any | None = None
    ) -> Dict[str, Any]: ...

    def list_tools(self) -> Dict[str, Dict[str, Any]]:  # noqa: D401
        ...

    def available_tools(self) -> list[str]:  # noqa: D401
        ...
