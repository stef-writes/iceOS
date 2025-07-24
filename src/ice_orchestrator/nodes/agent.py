"""Agent node - stateful reasoning with tools."""
from typing import Dict, Any, List, Optional
from ice_core.models import BaseNode

class AgentNode(BaseNode):
    """Autonomous agent with reasoning loop."""
    
    agent_ref: str
    tools: List[str] = []
    max_iterations: int = 10
    memory_config: Optional[Dict[str, Any]] = None
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent's reasoning loop."""
        from ice_sdk.unified_registry import registry
        from ice_core.models import NodeType
        
        # Get agent class and instantiate
        agent_class = registry.get_class(NodeType.AGENT, self.agent_ref)
        agent = agent_class(
            tools=self.tools,
            max_iterations=self.max_iterations,
            memory_config=self.memory_config
        )
        
        # Execute agent
        result = await agent.run(inputs)
        return result 