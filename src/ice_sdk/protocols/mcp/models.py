"""Pydantic models mirroring *docs/api/mcp.yaml* (alpha).

Only the properties needed by the current internal control-plane are defined.
Future optional fields can be added without breaking strict-mypy rules.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator

# ---------------------------------------------------------------------------
# Blueprint & nodes ----------------------------------------------------------
# ---------------------------------------------------------------------------


class NodeSpec(BaseModel):
    id: str
    type: str

    model_config = {"extra": "allow"}  # accept tool/ai-specific keys


class Blueprint(BaseModel):
    blueprint_id: str = Field(default_factory=lambda: "bp_" + uuid4_hex())
    version: str = "1.0.0"
    nodes: List[NodeSpec]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BlueprintAck(BaseModel):
    blueprint_id: str
    status: str  # accepted | updated


# ---------------------------------------------------------------------------
# Run helpers ----------------------------------------------------------------
# ---------------------------------------------------------------------------


class RunOptions(BaseModel):
    max_parallel: int = Field(5, ge=1, le=20)


class RunRequest(BaseModel):
    blueprint_id: Optional[str] = None
    blueprint: Optional[Blueprint] = None
    options: RunOptions = Field(default_factory=lambda: RunOptions(max_parallel=5))

    @model_validator(mode="after")
    def _at_least_one(self) -> "RunRequest":  # noqa: D401 – pydantic hook
        """Ensure one of *blueprint* or *blueprint_id* is supplied."""

        if self.blueprint is None and self.blueprint_id is None:
            raise ValueError("Either blueprint or blueprint_id must be provided")

        return self


class RunAck(BaseModel):
    run_id: str
    status_endpoint: HttpUrl
    events_endpoint: HttpUrl


class RunResult(BaseModel):
    run_id: str
    success: bool
    start_time: _dt.datetime
    end_time: _dt.datetime
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Utilities ------------------------------------------------------------------
# ---------------------------------------------------------------------------


def uuid4_hex() -> str:  # noqa: D401 – helper
    import uuid

    return uuid.uuid4().hex
