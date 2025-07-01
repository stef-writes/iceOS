"""Pydantic models for event payloads emitted by iceOS subsystems."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field

__all__ = [
    "CLICommandEvent",
    "EventEnvelope",
]


class CLICommandEvent(BaseModel):
    """Schema for CLI command lifecycle events."""

    command: str
    status: Literal["started", "completed", "failed"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    params: Dict[str, Any] = Field(default_factory=dict)


class EventEnvelope(BaseModel):
    """Generic wrapper so all events share a common outer structure."""

    name: str
    payload: BaseModel
    timestamp: datetime = Field(default_factory=datetime.utcnow)
