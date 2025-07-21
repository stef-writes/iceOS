"""Pydantic model for declarative *Network* specifications.

A *Network* is a high-level collection of nodes – including *nested_chain*
ones – that can be serialised in YAML/JSON and executed via
:pyfunc:`ice_orchestrator.core.network_factory.NetworkFactory.from_yaml`.

The schema purposefully mirrors the *ScriptChain* payload structure so that we
can reuse :class:`~ice_orchestrator.core.chain_factory.ChainFactory` with
minimal conversion logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["NetworkSpec"]


class NetworkMetadata(BaseModel):
    name: str = Field(...)
    description: Optional[str] = None
    version: str = Field("1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    tags: List[str] = Field(default_factory=list)


class NetworkValidationError(ValueError):
    """Raised when network spec validation fails."""

    def __init__(self, msg: str):
        super().__init__(f"Network validation failed: {msg}")
        self.error_code = "NETWORK_VALIDATION_ERROR"


class NetworkSpec(BaseModel):
    api_version: Literal["network.v1"] = "network.v1"
    id: str = Field(..., min_length=3, pattern=r"^[a-z0-9_-]+$")
    node_ids: list[str] = Field(default_factory=list)
    nodes: Dict[str, Dict[str, Any]] = Field(..., description="Node declarations")

    def validate(self) -> None:
        """Business logic validation separate from Pydantic schema checks."""
        if not self.node_ids:
            raise NetworkValidationError("At least one node ID required")
        if len(self.node_ids) != len(set(self.node_ids)):
            raise NetworkValidationError("Duplicate node IDs detected")

    model_config = ConfigDict(extra="forbid")
