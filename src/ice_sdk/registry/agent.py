from __future__ import annotations

"""Agent registry – central catalogue for reusable, stand-alone agents.

Parallels ``ice_sdk.registry.tool.ToolRegistry`` so that every executable entity
in iceOS (tools, units, agents, chains) follows the **exact same discovery and
lookup contract**.
"""

from typing import Any, Dict, Generator, Mapping, Tuple
import warnings

from pydantic import BaseModel, PrivateAttr

__all__: list[str] = [
    "AgentRegistry",
    "global_agent_registry",
]


class AgentRegistrationError(RuntimeError):
    """Raised when an agent cannot be registered in the registry."""


class AgentRegistry(BaseModel):
    """In-memory registry that resolves *Agent* implementations by name.

    The registry purposely stores **instances**, not classes, because Agents
    are allowed to preserve state (e.g., memory buffers).  Implementations
    SHOULD still be idempotent upon multiple instantiations to respect
    Rule 13 (`validate()` + `execute()` MUST be side-effect safe).
    """

    _agents: Dict[str, Any] = PrivateAttr(default_factory=dict)

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
    }

    # ------------------------------------------------------------------ API
    def register(self, name: str, agent: Any) -> None:  # noqa: D401 – generic Any for now
        """Add *agent* under *name*.

        Validation is delegated to the agent's own ``validate()`` method when
        present.  Duplicate names raise :class:`AgentRegistrationError` to
        prevent accidental shadowing.
        """

        if name in self._agents:
            raise AgentRegistrationError(f"Agent '{name}' already registered")

        # Best-effort validation hook
        validate_fn = getattr(agent, "validate", None)
        if callable(validate_fn):
            validate_fn()

        self._agents[name] = agent

    def get(self, name: str) -> Any:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise AgentRegistrationError(f"Agent '{name}' not found") from exc

    async def execute(self, name: str, payload: Mapping[str, Any]) -> Any:
        """Run ``agent.execute`` with *payload* and return result – async aware."""

        agent = self.get(name)
        exec_fn = getattr(agent, "execute")
        if not callable(exec_fn):
            raise TypeError(f"Agent '{name}' has no callable 'execute' method")

        import asyncio
        if asyncio.iscoroutinefunction(exec_fn):
            return await exec_fn(payload)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, exec_fn, payload)

    # ------------------------------------------------------------------ helpers
    def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
        yield from self._agents.items()

    def __len__(self) -> int:  # pragma: no cover – convenience
        return len(self._agents)


# Global default instance ----------------------------------------------------

global_agent_registry: "AgentRegistry[Any]" = AgentRegistry()  # type: ignore[type-var]

# Legacy alias shim ----------------------------------------------------------
import sys as _sys

_sys.modules.setdefault(
    "ice_sdk.registry.agents",  # plural form
    _sys.modules[__name__],
)

warnings.warn(
    "'global_agent_registry' has moved to 'ice_sdk.registry.agent'; update imports.",
    DeprecationWarning,
    stacklevel=2,
) 