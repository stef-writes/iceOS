from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from ice_core.models.llm import LLMConfig
from ice_core.models import BaseNode

class AgentNodeConfig(BaseModel):
    """Configuration for an AI agent node."""

    llm_config: LLMConfig = Field(..., description="LLM provider configuration")
    system_prompt: str = Field(..., min_length=10, description="Base system prompt")
    max_retries: int = Field(3, ge=0, description="Max automatic retry attempts")
    tools: list[str] = Field(default_factory=list, description="Allowed tool names")

class AgentNode(BaseNode):
    """Orchestratable agent node combining LLM reasoning with tool usage."""

    def __init__(
        self,
        config: AgentNodeConfig,
        *,
        context_manager: Any | None = None,  # noqa: ANN401 – avoids circular import
    ) -> None:
        super().__init__(node_type="agent")
        self.config = config
        self.context_manager = context_manager  # may be None until runtime
        self.tools: List[Any] = []  # populated by orchestrator during wiring
        self._context: Dict[str, Any] = {}

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent's decision loop with error handling."""
        try:
            return await self._execute_agent_cycle(inputs)
        except Exception as e:
            return self._handle_agent_error(e)

    async def _execute_agent_cycle(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Core agent logic would integrate with LLM service
        return {
            "status": "success",
            "output": f"Agent processed {len(inputs)} inputs",
            "usage": {"tokens": 42},
        }

    def _handle_agent_error(self, error: Exception) -> Dict[str, Any]:
        return {
            "status": "error",
            "error_type": type(error).__name__,
            "message": str(error),
        }

    def validate(self) -> None:
        """Pre-execution validation."""
        if not self.config.tools:
            raise ValueError("AgentNode requires at least one allowed tool")
