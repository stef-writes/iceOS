"""Agent node executor for the orchestrator."""
from typing import Dict, Any
from ice_orchestrator.agent import AgentNode as BaseAgentNode, AgentExecutor


class AgentNodeExecutor:
    """Executes agent nodes within workflow orchestration."""
    
    @staticmethod
    async def execute(node: BaseAgentNode, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an agent node."""
        executor = AgentExecutor()
        return await executor.execute_agent(node, inputs) 