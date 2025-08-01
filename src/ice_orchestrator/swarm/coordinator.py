"""Swarm coordination orchestrator."""
from typing import Dict, Any
from ice_core.models.node_models import SwarmNodeConfig
from ice_core.unified_registry import registry
from ice_core.models import NodeType
from ice_sdk.services.locator import ServiceLocator
from .strategies import SwarmStrategy

class SwarmCoordinator:
    """Orchestrates multi-agent coordination using different strategies."""
    
    def __init__(self, config: SwarmNodeConfig):
        self.config = config
        
    async def coordinate(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate swarm execution using configured strategy."""
        # Get shared memory pool for coordination
        shared_memory = ServiceLocator.get("shared_memory")
        pool = await shared_memory.get_pool("swarm_coordination")  # Use default pool name
        
        # Load agents from registry
        agents = []
        for agent_spec in self.config.agents:
            agent = registry.get_instance(NodeType.AGENT, agent_spec.package)
            agents.append((agent, agent_spec))
        
        # Execute coordination strategy
        strategy: SwarmStrategy
        if self.config.coordination_strategy == "consensus":
            from .strategies import ConsensusStrategy
            strategy = ConsensusStrategy(self.config)
        elif self.config.coordination_strategy == "hierarchical":
            from .strategies import HierarchicalStrategy  
            strategy = HierarchicalStrategy(self.config)
        elif self.config.coordination_strategy == "marketplace":
            from .strategies import MarketplaceStrategy
            strategy = MarketplaceStrategy(self.config)
        else:
            raise ValueError(f"Unknown coordination strategy: {self.config.coordination_strategy}")
        
        # Execute strategy
        result = await strategy.execute(agents, inputs, pool)
        
        return result 