"""Swarm node - multi-agent coordination."""
from typing import Dict, Any
from ice_core.base_node import BaseNode
from ice_core.models.node_models import SwarmNodeConfig

class SwarmNode(BaseNode):
    """Multi-agent swarm coordination node with consensus/hierarchical/marketplace strategies."""
    
    config: SwarmNodeConfig
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "consensus_reached": {"type": "boolean"},
                "final_result": {"type": "object"},
                "coordination_strategy": {"type": "string"},
                "rounds_completed": {"type": "integer"},
                "all_proposals": {"type": "array"}
            },
            "required": ["consensus_reached", "final_result", "coordination_strategy"]
        }
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task for swarm to coordinate on"},
                "context": {"type": "object", "description": "Shared context for all agents"}
            },
            "required": ["task"]
        }
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute swarm coordination through coordinator delegation."""
        from .coordinator import SwarmCoordinator
        
        # Create coordinator with our configuration
        coordinator = SwarmCoordinator(self.config)
        
        # Execute swarm coordination
        result = await coordinator.coordinate(inputs)
        
        return result 