from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field, PrivateAttr

from ice_core.base_node import BaseNode
from ice_core.models.node_models import (
    AgentNodeConfig,
    NodeExecutionResult,
    NodeMetadata,
)


from ice_core.protocols import validated_protocol

@validated_protocol("agent")
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

    async def execute(self, inputs: Dict[str, Any]) -> NodeExecutionResult:
        """Execute agent's decision loop with error handling."""
        try:
            result = await self._execute_agent_cycle(inputs)
            return NodeExecutionResult(
                success=True,
                output=result,
                error=None,
                metadata=NodeMetadata(
                    node_id=self.config.id, 
                    node_type="agent",
                    name=self.config.name or "AgentNode"
                )  # type: ignore[call-arg]
            )
        except Exception as e:
            return NodeExecutionResult(
                success=False,
                output=None,
                error=str(e),
                metadata=NodeMetadata(
                    node_id=self.config.id, 
                    node_type="agent",
                    name=self.config.name or "AgentNode"
                )  # type: ignore[call-arg]
            )

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

    def allowed_tools(self) -> List[str]:
        """Return list of tool names allowed for this agent."""
        return [getattr(t, "name", "<unknown>") for t in self.tools]

    async def think(self, context: Dict[str, Any]) -> str:  # noqa: D401 – imperative OK
        """Simple reasoning stub – replace with real chain-of-thought."""
        return f"Thinking over {len(context)} keys"

    async def validate_config(self) -> None:
        """Pre-execution validation."""
        if not self.config.tools:
            raise ValueError("AgentNode requires at least one allowed tool")
        
    @property
    def system_prompt(self) -> str:
        """Get system prompt from agent config."""
        return str(self.config.agent_config.get("system_prompt", "You are a helpful AI assistant."))
    
    @property
    def max_retries(self) -> int:
        """Get max retries from agent config."""
        return int(self.config.agent_config.get("max_retries", 3))
