"""Agent protocol definition.

Defines the minimal additional contract an *agent node* must satisfy beyond the
core `INode` interface. Keeping this tiny avoids over-coupling while still
providing compile-time guarantees that the orchestrator can rely on.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class IAgent(Protocol):
    """Behavioural contract for agent-style nodes.

    Agents combine LLM reasoning with tool usage.  Only the two methods below
    are *strictly* required for orchestration; anything else lives on concrete
    subclasses.
    """

    # ---------------------------------------------------------------------
    # High-level actions
    # ---------------------------------------------------------------------

    @abstractmethod
    async def think(self, context: Dict[str, Any]) -> str:  # noqa: D401 – imperative verb fine
        """Produce an internal reasoning trace / next action decision."""

    @abstractmethod
    def allowed_tools(self) -> List[str]:
        """Return list of tool names the agent may invoke during execution."""
