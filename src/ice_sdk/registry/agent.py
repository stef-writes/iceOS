from __future__ import annotations

"""Agent registry – canonical home for reusable AgentNode classes.

The registry enables short-name discovery of agents that can be reused across
workflows (via ``agent`` nodes) instead of relying on a fully-qualified import
path every time.

Usage
-----
>>> from ice_sdk.registry.agent import global_agent_registry
>>> global_agent_registry.register("smart_planner", SmartPlannerAgent)
>>> AgentCls = global_agent_registry.get("smart_planner")
"""

from typing import Any, Dict, Generator, Mapping, Type, Tuple

from pydantic import BaseModel, PrivateAttr

from ice_sdk.agents.agent_node import AgentNode  # runtime base class

__all__: list[str] = [
    "AgentRegistry",
    "global_agent_registry",
]


class AgentRegistrationError(RuntimeError):
    """Raised when an agent cannot be registered in the registry."""


class AgentRegistry(BaseModel):
    """In-memory registry that resolves *AgentNode* classes by name.

    Mirrors *ToolRegistry* behaviour so orchestration can load agents by a
    stable identifier instead of import strings.
    """

    # Internal mapping – excluded from model schema
    _agents: Dict[str, Type[AgentNode]] = PrivateAttr(default_factory=dict)

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
    }

    # ------------------------------------------------------------------ API
    def register(self, name: str, agent_cls: Type[AgentNode]) -> None:
        """Register *agent_cls* under *name*.

        Parameters
        ----------
        name : str
            Public identifier used by workflows.
        agent_cls : Type[AgentNode]
            Concrete :class:`~ice_sdk.agents.agent_node.AgentNode` subclass.
        """

        if name in self._agents:
            raise AgentRegistrationError(f"Agent '{name}' already registered")

        # Optional: call class-level validate() if present ----------------
        validate_fn = getattr(agent_cls, "validate", None)
        if callable(validate_fn):
            # Most AgentNode.validate() methods are instance-based; attempt safe call
            try:
                validate_fn(agent_cls)  # type: ignore[arg-type]
            except TypeError:
                # Fallback – instantiate with minimal args if signature requires self
                try:
                    instance = agent_cls.__new__(agent_cls)  # type: ignore[misc]
                    validate_fn(instance)  # type: ignore[arg-type]
                except Exception:  # pragma: no cover – do not block registration
                    pass

        self._agents[name] = agent_cls

    def get(self, name: str) -> Type[AgentNode]:
        """Return the registered AgentNode class for *name*."""

        try:
            return self._agents[name]
        except KeyError as exc:
            raise AgentRegistrationError(f"Agent '{name}' not found") from exc

    # Convenience helpers -------------------------------------------------
    def __iter__(self) -> Generator[Tuple[str, Type[AgentNode]], None, None]:
        yield from self._agents.items()

    def __len__(self) -> int:  # noqa: D401 – dunder helper
        return len(self._agents)


# Global default instance ----------------------------------------------------

global_agent_registry: "AgentRegistry[Any]" = AgentRegistry()  # type: ignore[type-var] 