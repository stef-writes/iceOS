from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field

__all__: list[str] = ["WorkflowSession"]


class WorkflowSession(BaseModel):
    """Conversation-scoped storage for design answers."""

    answers: Dict[str, str] = Field(default_factory=dict)
