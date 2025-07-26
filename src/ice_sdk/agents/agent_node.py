from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, PrivateAttr

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
    
    config: AgentNodeConfig
    context_manager: Optional[Any] = None  # noqa: ANN401 – avoids circular import
    tools: List[Any] = Field(default_factory=list, description="Tools populated by orchestrator")
    _context: Dict[str, Any] = PrivateAttr(default_factory=dict)
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Input schema for agent node."""
        return {"type": "object", "properties": {"query": {"type": "string"}}}
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        """Output schema for agent node."""
        return {"type": "object", "properties": {"response": {"type": "string"}}}

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
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Implement required method from BaseNode."""
        return await self._execute_agent_cycle(inputs)

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
