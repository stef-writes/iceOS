"""Parameter schema for *AgentSkill* instances.

Located inside ``ice_sdk.models`` to avoid cross-layer imports and to keep
agent-specific logic out of the core schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__: list[str] = ["AgentParams"]


class AgentParams(BaseModel):
    """Runtime configuration passed into an *AgentSkill*.

    Attributes
    ----------
    system_prompt: str
        Base system prompt injected before user messages.
    allowed_tools: list[str]
        Whitelisted skill identifiers the agent may invoke.
    memory_context: str, default "session"
        Scope of conversational memory ("session", "user", etc.).
    """

    system_prompt: str
    allowed_tools: list[str] = Field(..., min_items=1)
    memory_context: str = "session"
