"""Agent runtime service: planning loop, tool selection, and memory updates.

This keeps agent execution semantics out of the executor and allows us to
iterate on the planning API without touching node contracts.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Protocol

from ice_orchestrator.services.tool_execution_service import ToolExecutionService


class _ReasoningAgent(Protocol):  # minimal duck-typed protocol
    async def think(self, context: Dict[str, Any]) -> str: ...  # noqa: D401

    def allowed_tools(self) -> List[str]: ...  # noqa: D401

    # Optional advanced planning hook returning structured action
    # {"tool": str, "inputs": dict, "done": bool, "message": str}
    # Method can be sync or async and is optional.
    def decide(self, context: Dict[str, Any]) -> Dict[str, Any]: ...  # type: ignore[empty-body]  # noqa: D401


class AgentRuntime:
    """Execute an agent node with simple plan→act→observe semantics.

    The loop attempts to call ``decide`` when present, otherwise falls back to
    a single ``think`` step. Tool execution is restricted by ``allowed_tools``
    when provided by the agent implementation.
    """

    def __init__(self, tool_executor: ToolExecutionService | None = None) -> None:
        self._tool_executor = tool_executor or ToolExecutionService()

    async def run(
        self,
        agent: _ReasoningAgent,
        *,
        context: Dict[str, Any],
        max_iterations: int = 5,
    ) -> Dict[str, Any]:
        """Run the agent with a bounded number of plan/act iterations.

        Parameters
        ----------
        agent : _ReasoningAgent
            Concrete agent instance implementing ``think`` and optionally
            ``decide``/``allowed_tools``.
        context : dict
            Mutable execution context. Tool results are merged under
            ``context['agent']`` for transparency.
        max_iterations : int
            Safety bound to prevent infinite loops.

        Returns
        -------
        dict[str, Any]
            Final agent output including reasoning trace and last tool result.
        """

        reasoning: List[str] = []
        allowed = []
        try:
            allowed = agent.allowed_tools()
        except Exception:
            allowed = []

        for _ in range(max(1, max_iterations)):
            action: Dict[str, Any] | None = None
            # Prefer structured decide() if present
            decide_attr = getattr(agent, "decide", None)
            if decide_attr is not None:
                if asyncio.iscoroutinefunction(decide_attr):
                    action = await decide_attr(context)
                else:
                    action = decide_attr(context)  # type: ignore[misc]
            else:
                # Fall back to a single think() step and exit
                thought = await agent.think(context)
                reasoning.append(thought)
                return {
                    "reasoning": reasoning,
                    "message": thought,
                }

            # Record any self-reported thought
            msg = action.get("message") if action else None
            if isinstance(msg, str) and msg:
                reasoning.append(msg)

            # Termination without acting
            if action and action.get("done") is True and not action.get("tool"):
                return {
                    "reasoning": reasoning,
                    "message": msg or "done",
                }

            # Tool decision path
            if action and action.get("tool"):
                tool_name = str(action["tool"])  # normalize
                if allowed and tool_name not in allowed:
                    raise ValueError(f"Tool '{tool_name}' not permitted by agent")
                inputs = action.get("inputs") or {}
                if not isinstance(inputs, dict):
                    raise ValueError("Agent 'inputs' must be a mapping")

                result = await self._tool_executor.execute_tool(
                    tool_name, inputs, context
                )

                # Update context under 'agent'
                agent_ctx = context.setdefault("agent", {})
                agent_ctx["last_tool"] = tool_name
                agent_ctx["last_result"] = result

                # Optional observe() callback
                observe_attr = getattr(agent, "observe", None)
                if callable(observe_attr):
                    try:
                        if asyncio.iscoroutinefunction(observe_attr):
                            await observe_attr(context, result)
                        else:
                            observe_attr(context, result)  # type: ignore[misc]
                    except Exception:
                        # Observation is best-effort
                        pass

                # Check termination flag after act
                if action.get("done") is True:
                    return {
                        "reasoning": reasoning,
                        "last_tool": tool_name,
                        "result": result,
                        "message": msg or "done",
                    }
                # Continue loop to allow multi-step plans
                continue

            # If no tool selected and not done – treat as final message
            return {
                "reasoning": reasoning,
                "message": msg or "",
            }

        # Safety exit if loop exhausted
        return {
            "reasoning": reasoning,
            "message": "max_iterations reached",
        }
