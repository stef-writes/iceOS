"""Context types for SDK."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class ToolContext(BaseModel):
    """Lightweight context passed to tools."""

    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


__all__ = ["ToolContext"]
