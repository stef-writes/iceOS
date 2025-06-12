from __future__ import annotations

from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field

from ice_agents.node_agent_adapter import NodeAgentAdapter
from ice_sdk.context.session_state import SessionState
from ice_sdk.base_tool import BaseTool


class _GenericParams(BaseModel):
    """Accept arbitrary JSON properties as input context for the agent."""

    input: Dict[str, Any] = Field(
        default_factory=dict, description="Input context forwarded to the agent"
    )

    model_config = {
        "extra": "allow",
    }


class AgentTool(BaseTool):
    """Wrap a *NodeAgentAdapter* so it can be called as a Tool in AiNode."""

    def __init__(
        self,
        agent: NodeAgentAdapter,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.agent = agent
        self.name = name or f"{agent.name}_tool"
        self.description = description or f"Call underlying agent '{agent.name}'"
        self.parameters_schema: Type[BaseModel] = _GenericParams  # type: ignore[assignment]
        self.output_schema = None

    # The framework may run `run` synchronously or asynchronously.
    async def run(self, *, input: Dict[str, Any], **kwargs):  # type: ignore[override]  # noqa: D401
        session = SessionState("agent_tool_call")
        result = await self.agent.execute(session, input)
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }
