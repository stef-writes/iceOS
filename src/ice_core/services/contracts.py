from __future__ import annotations

"""Service-level helpers for loading and validating API contracts.

This module centralises any *operational* logic around version-negotiation and
contract discovery so that callers use a stable, idempotent interface –
conforming to iceOS repo rule 11 (all cross-layer calls go through services/*).
"""

from pathlib import Path
from typing import Final, Protocol
from typing_extensions import runtime_checkable

from ice_core.models.service_contracts import ServiceContract

# Directory where JSON/YAML contract artefacts will live.  This keeps data
# outside the package code for cleaner upgrades.
_CONTRACTS_DIR: Final[Path] = (
    Path(__file__).resolve().parent.parent / "contracts"
)


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
    def __init__(self):
        self._validate_contract() 