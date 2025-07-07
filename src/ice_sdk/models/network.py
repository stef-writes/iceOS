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

from pydantic import BaseModel, Field

__all__ = ["NetworkSpec"]


class NetworkMetadata(BaseModel):
    name: str = Field(...)
    description: Optional[str] = None
    version: str = Field("1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    tags: List[str] = Field(default_factory=list)


class NetworkSpec(BaseModel):
    api_version: Literal["network.v1"] = "network.v1"
    metadata: NetworkMetadata = Field(default_factory=NetworkMetadata)  # type: ignore[arg-type]
    nodes: Dict[str, Dict[str, Any]] = Field(
        ..., description="Node declarations keyed by node id"
    )

    class Config:
        extra = "forbid"
