"""Agent-as-a-Tool wrapper (core).

Enables one agent to call another agent via the standard Tool interface. This keeps
composition uniform: agents can mount tools, and tools can wrap agents, while the
runtime remains executor-centric.

Design notes
- Tool lives in core (not orchestrator) to respect layer boundaries.
- Only side-effects occur inside the tool's `_execute_impl` per project rules.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from ice_core.base_tool import ToolBase
from ice_core.exceptions import ValidationError

__all__: list[str] = ["AgentTool"]


class AgentTool(ToolBase):
    """Wrap an agent instance so it can be mounted as a normal tool.

    Args:
        agent (Any): An object exposing ``execute`` as ``async def`` or sync def
            with signature ``(inputs: Dict[str, Any]) -> Dict[str, Any]``.
        name (Optional[str]): Override tool name. Defaults to agent.name or a
            derived identifier.
        skip_summarization (bool): Reserved option for parity with external
            designs. Currently a no-op.

    Example:
        >>> class Greeter:
        ...     async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        ...         return {"greeting": f"Hello, {inputs.get('name', 'world')}!"}
        >>> tool = AgentTool(agent=Greeter())
        >>> import asyncio
        >>> asyncio.run(tool.execute(name="Ice"))
        {'greeting': 'Hello, Ice!'}
    """

    # Runtime attributes ---------------------------------------------------
    agent: Any  # dynamic agent type; validated at runtime
    skip_summarization: bool = False

    # Metadata – will be derived from the wrapped agent by __init__ ----------
    name: str = ""
    description: str = ""

    def __init__(
        self,
        agent: Any,
        *,
        name: Optional[str] = None,
        skip_summarization: bool = False,
    ) -> None:
        # Derive friendly metadata from agent
        derived_name: str = str(
            name or getattr(agent, "name", f"agent_tool_{id(agent):x}")
        )
        derived_description: str = str(
            getattr(agent, "description", "Agent wrapped as tool")
        )

        # Initialise BaseModel fields ensuring Pydantic validation runs
        super().__init__(  # type: ignore[call-arg]
            agent=agent,
            skip_summarization=skip_summarization,
            name=derived_name,
            description=derived_description,
        )

        # No implicit instance registration; factories are preferred in v1

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Delegate to the wrapped agent's ``execute``.

        Raises:
            ValidationError: If the wrapped agent does not expose an ``execute``
                function/coroutine.
        Returns:
            Dict[str, Any]: The agent's output.
        """
        if not hasattr(self.agent, "execute"):
            raise ValidationError("Wrapped agent must define an 'execute' method")

        execute_fn = getattr(self.agent, "execute")

        if asyncio.iscoroutinefunction(execute_fn):
            from typing import cast

            return cast(Dict[str, Any], await execute_fn(kwargs))  # type: ignore[arg-type]

        # Fallback – run synchronous execute in a thread pool
        from typing import cast

        return cast(Dict[str, Any], await asyncio.to_thread(execute_fn, kwargs))  # type: ignore[arg-type]

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Accept any JSON input – enforcement is delegated to the agent."""
        return {"type": "object", "additionalProperties": True}

    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Open schema – agent output is opaque at this layer."""
        return {"type": "object"}
