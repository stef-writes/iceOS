"""Lightweight Pydantic models used by the public iceos-client package.

These mirror the wire contracts exposed by the API but avoid importing
server-internal modules. Keeping models local ensures the client can be
distributed independently on PyPI without dragging in server code.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeSpec(BaseModel):
    """JSON-friendly node description (same keys as NodeConfig)."""

    id: str
    type: str
    dependencies: List[str] = Field(default_factory=list)

    # Accept arbitrary extra fields so callers can embed the full NodeConfig.
    model_config = {"extra": "allow"}


class Blueprint(BaseModel):
    """A design-time workflow blueprint transferable over the wire."""

    blueprint_id: str = Field(default_factory=lambda: f"bp_{uuid.uuid4().hex[:8]}")
    schema_version: str = Field("1.2.0")
    nodes: List[NodeSpec]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RunAck(BaseModel):
    """Acknowledgement for run start (MCP `/runs`)."""

    run_id: str
    status_endpoint: str
    events_endpoint: str


class RunResult(BaseModel):
    """Result of workflow execution (MCP `/runs/{id}`)."""

    run_id: str
    success: bool
    start_time: _dt.datetime
    end_time: _dt.datetime
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
