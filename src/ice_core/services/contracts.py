"""Service contracts and protocols for cross-layer communication.

This module defines the interfaces that different layers of iceOS use to
communicate without violating architectural boundaries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Protocol, runtime_checkable

from pydantic import BaseModel


class ServiceContract(BaseModel):
    """Contract definition for a microservice."""

    version: str
    name: str
    endpoints: List[str] = []


def load_current(service_name: str) -> ServiceContract:
    """Return the *current* contract for *service_name*.

    Parameters
    ----------
    service_name : str
        The top-level service package name (e.g. ``"ice_api"``).

    Returns
    -------
    ServiceContract
        Parsed and validated contract object.

    Examples
    --------
    >>> from ice_core.services.contracts import load_current
    >>> contract = load_current("ice_api")
    >>> print(contract.version)
    0.1.0
    """

    # Service contract loading from YAML not yet implemented
    return ServiceContract(version="0.1.0", name=service_name)


@runtime_checkable
class MicroserviceContract(Protocol):
    """Base protocol for microservice implementations."""

    def validate_api_surface(self) -> bool:
        """Validate the API surface matches the contract."""
        ...


class NodeService(MicroserviceContract):
    def __init__(self, service_name: str = "ice_core"):
        # Load the declared contract for the micro-service and validate once
        self._contract: ServiceContract = load_current(service_name)
        self._validate_contract()

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------

    def _validate_contract(self) -> None:  # – simple helper
        """Validate that the loaded contract adheres to basic invariants.

        At this stage the *ServiceContract* model itself performs strict
        schema validation via **pydantic**, therefore we only need a very
        lightweight runtime assertion.  The helper exists primarily so that
        higher-level services can override it with domain-specific checks
        once real contract artefacts are introduced.
        """

        if not self._contract.version:
            from ice_core.exceptions import ValidationError

            raise ValidationError("ServiceContract.version must be a non-empty string")


@runtime_checkable
class IWorkflowService(Protocol):
    """Protocol for executing workflows without leaking orchestrator types."""

    @abstractmethod
    async def execute(
        self,
        nodes: list[Any],  # NodeConfig-compatible payloads
        name: str,
        max_parallel: int = 5,
        *,
        run_id: str | None = None,
        event_emitter: Any | None = None,
    ) -> Any: ...

    @abstractmethod
    async def get_workflow(self, workflow_id: str) -> Any: ...

    @abstractmethod
    async def create_partial_blueprint(self) -> str: ...


@runtime_checkable
class IBuilderService(Protocol):
    """Protocol for workflow builder services (implemented in SDK layer)."""

    @abstractmethod
    def create_workflow(self, name: str) -> Any:
        """Create a new workflow builder instance"""
        ...

    @abstractmethod
    def add_node(
        self, builder: Any, node_type: str, node_id: str, **config: Any
    ) -> Any:
        """Add a node to the workflow"""
        ...

    @abstractmethod
    def connect(self, builder: Any, from_node: str, to_node: str) -> Any:
        """Connect two nodes in the workflow"""
        ...

    @abstractmethod
    def build(self, builder: Any) -> Any:
        """Build the final workflow from the builder"""
        ...

    @abstractmethod
    def to_dict(self, builder: Any) -> dict[str, Any]:
        """Export workflow as dictionary"""
        ...


class NetworkStorage(ABC):
    @abstractmethod
    async def get(self, spec_id: str) -> dict[str, Any] | None:
        pass

    @abstractmethod
    async def put(self, spec_id: str, spec: dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def query(self, filter: str) -> list[dict[str, Any]]:
        pass
