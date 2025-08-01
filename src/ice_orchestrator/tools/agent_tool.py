"""Agent-as-a-Tool wrapper similar to Google ADK's `AgentTool`.

Allows one agent to call another agent as if it were a deterministic tool.
After execution, control returns to the caller agent – i.e. this is *not* a
sub-agent hand-off where responsibility is permanently delegated.

NOTE: Because iceOS currently has no concrete multi-agent runtime contract, the
wrapper simply calls an `execute` coroutine on the wrapped agent.  This is
sufficient for unit-testing and incremental integration; a richer interface
(task queues, summarisation) can be added later.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from ice_core.base_tool import ToolBase
from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry

__all__: list[str] = ["AgentTool"]

class AgentTool(ToolBase):
    """Wrap an agent instance so it can be mounted as a normal tool."""

    # Runtime attributes ---------------------------------------------------

    agent: Any  # noqa: ANN401 – avoid cross-layer import for now
    skip_summarization: bool = False  # mirrors ADK option – no-op placeholder

    # Metadata – will be filled from the wrapped agent by __init__ ----------

    name: str = ""
    description: str = ""

    # ---------------------------------------------------------------------
    # Construction helpers -------------------------------------------------
    # ---------------------------------------------------------------------

    def __init__(
        self,
        agent: Any,  # noqa: ANN401 – dynamic agent type
        *,
        name: Optional[str] = None,
        skip_summarization: bool = False,
    ) -> None:
        # ------------------------------------------------------------------
        # Pydantic BaseModel initialisation ---------------------------------
        # ------------------------------------------------------------------
        derived_name: str = str(name or getattr(agent, "name", f"agent_tool_{id(agent):x}"))
        derived_description: str = str(getattr(agent, "description", "Agent wrapped as tool"))

        # Call BaseModel.__init__ with field values so Pydantic validation
        # still happens.
        # Pydantic BaseModel accepts arbitrary keyword fields corresponding
        # to annotated attributes, but *mypy* cannot see this dynamic behaviour
        # (https://docs.pydantic.dev/latest/usage/mypy/).  We therefore silence
        # the false-positive with a narrow type ignore.
        super().__init__(  # type: ignore[call-arg]
            agent=agent,
            skip_summarization=skip_summarization,
            name=derived_name,
            description=derived_description,
        )

        # Auto-register the instance for discovery – validation disabled to
        # avoid circular dependencies during bootstrapping.
        registry.register_instance(NodeType.TOOL, self.name, self, validate=False)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Tool execution ----------------------------------------------------
    # ------------------------------------------------------------------

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Delegate the call to the wrapped agent.

        Expected agent API: ``await agent.execute(inputs: Dict[str, Any])``.
        If the agent exposes a synchronous ``execute`` we run it in a thread.
        """
        if not hasattr(self.agent, "execute"):
            raise AttributeError("Wrapped agent has no 'execute' coroutine/function")

        execute_fn = getattr(self.agent, "execute")

        if asyncio.iscoroutinefunction(execute_fn):
            from typing import cast
            return cast(Dict[str, Any], await execute_fn(kwargs))  # type: ignore[arg-type]
        # Fallback – run sync execute in thread pool
        from typing import cast
        return cast(Dict[str, Any], await asyncio.to_thread(execute_fn, kwargs))  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Schema helpers ----------------------------------------------------
    # ------------------------------------------------------------------

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:  # noqa: D401 – keep same signature
        """Accept *any* JSON input – actual enforcement is done by the agent."""
        return {"type": "object", "additionalProperties": True}

    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:  # noqa: D401 – keep same signature
        """Return open schema – we can't predict agent output at this layer."""
        return {"type": "object"}
