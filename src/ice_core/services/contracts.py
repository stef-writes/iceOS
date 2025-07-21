from __future__ import annotations

# ruff: noqa: E402
# mypy: disable-error-code="misc,attr-defined,empty-body,name-defined"
"""Service-level helpers for loading and validating API contracts.

This module centralises any *operational* logic around version-negotiation and
contract discovery so that callers use a stable, idempotent interface –
conforming to iceOS repo rule 11 (all cross-layer calls go through services/*).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Final, List, Optional, Protocol

from typing_extensions import runtime_checkable

from ice_core.models.service_contracts import ServiceContract

# Runtime dependency only used for type-check paths – avoid import cycles.
# Importing **inside** TYPE_CHECKING avoids runtime layer violation while still
# providing correct typing for static analysis.  The layer guard inspects raw
# AST so even TYPE_CHECKING imports are flagged.  Therefore we avoid importing
# from higher layers entirely and rely on *Any* for those references.


# Directory where JSON/YAML contract artefacts will live.  This keeps data
# outside the package code for cleaner upgrades.
_CONTRACTS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "contracts"


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

    # NOTE: For now we return a placeholder until real contract files exist.
    # In the future this will locate `<_CONTRACTS_DIR>/<service_name>.json` (or
    # .yaml), load it, and validate via :class:`ServiceContract`.
    _ = service_name  # Placeholder – keep the signature stable
    return ServiceContract(version="0.1.0")


# Revised with protocol enforcement
class MicroserviceContract(Protocol):
    @runtime_checkable
    class Protocol(Protocol):
        def validate_api_surface(self) -> bool:
            """Ensures backward compatibility"""


class NodeService(MicroserviceContract):
    def __init__(self, service_name: str = "ice_core"):
        # Load the declared contract for the micro-service and validate once
        self._contract: ServiceContract = load_current(service_name)
        self._validate_contract()

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------

    def _validate_contract(self) -> None:  # noqa: D401 – simple helper
        """Validate that the loaded contract adheres to basic invariants.

        At this stage the *ServiceContract* model itself performs strict
        schema validation via **pydantic**, therefore we only need a very
        lightweight runtime assertion.  The helper exists primarily so that
        higher-level services can override it with domain-specific checks
        once real contract artefacts are introduced.
        """

        if not self._contract.version:
            raise ValueError("ServiceContract.version must be a non-empty string")


@runtime_checkable
class SkillServiceProtocol(Protocol):
    @abstractmethod
    async def execute_skill(
        self, skill_name: str, inputs: Dict[str, Any], timeout: float = 5.0
    ) -> Dict[str, Any]: ...


class SkillService:
    def __init__(self, registry: Optional[Any]):
        self._registry = registry

    async def execute_skill(
        self, skill_name: str, inputs: Dict[str, Any], timeout: float = 5.0
    ) -> Dict[str, Any]:
        # ... existing implementation ...
        pass  # Placeholder for actual implementation


@runtime_checkable
class IWorkflowService(Protocol):
    """Protocol for executing workflows without leaking orchestrator types."""

    @abstractmethod
    async def execute(
        self,
        nodes: list[Any],  # NodeConfig-compatible payloads
        name: str,
        max_parallel: int = 5,
    ) -> Any: ...


@runtime_checkable
class IBuilderService(Protocol):
    """Protocol for chain builder services (implemented in SDK layer)."""
    
    @abstractmethod
    def start(self, total_nodes: int, chain_name: str | None = None) -> Any:
        """Initialize a new chain draft"""
        ...
    
    @abstractmethod 
    def next_question(self, draft: Any) -> Any | None:
        """Get next configuration question"""
        ...
    
    @abstractmethod
    def submit_answer(self, draft: Any, key: str, answer: str) -> None:
        """Process user answer"""
        ...
    
    @abstractmethod
    def render_chain(self, draft: Any) -> str:
        """Generate chain visualization"""
        ...
    
    @abstractmethod 
    def render_mermaid(self, draft: Any) -> str:
        """Generate MermaidJS diagram"""
        ...


class NetworkStorage(ABC):
    @abstractmethod
    async def get(self, spec_id: str) -> Optional[dict]:
        pass
    
    @abstractmethod
    async def put(self, spec_id: str, spec: dict) -> None:
        pass
    
    @abstractmethod
    async def query(self, filter: str) -> List[dict]:
        pass
