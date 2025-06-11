from __future__ import annotations

from typing import Dict, Iterable

from .node_agent_adapter import NodeAgentAdapter


class AgentRegistry:
    """In-memory registry mapping *agent name* ➜ :class:`NodeAgentAdapter`.

    It is intentionally minimal; swap for Redis, SQL, etc. later by
    implementing the same interface.
    """

    def __init__(self):
        self._agents: Dict[str, NodeAgentAdapter] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def register(
        self, agent: NodeAgentAdapter, *, overwrite: bool = False
    ) -> None:  # noqa: D401
        if not overwrite and agent.name in self._agents:
            raise ValueError(f"Agent name '{agent.name}' already registered")
        self._agents[agent.name] = agent

    def get(self, name: str) -> NodeAgentAdapter:  # noqa: D401
        try:
            return self._agents[name]
        except KeyError as exc:
            raise KeyError(f"Agent '{name}' not found in registry") from exc

    def all(self) -> Iterable[NodeAgentAdapter]:  # noqa: D401
        return self._agents.values()

    # Convenience sugar ----------------------------------------------------
    def __contains__(self, name: str) -> bool:  # noqa: D401
        return name in self._agents

    def __iter__(self):  # noqa: D401
        return iter(self._agents.values())
