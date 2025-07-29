1"""Agent registry initialization."""

from ice_core.unified_registry import global_agent_registry


def initialize_agent_registry():
    """Register core agents in the global registry.
    
    NOTE: Agent runtime implementations have moved to ice_orchestrator.agent
    """
    # Register Memory Agent
    global_agent_registry.register_agent(
        "memory",
        "ice_orchestrator.agent.memory.MemoryAgent"
    )
    
    # Register base agent
    global_agent_registry.register_agent(
        "agent", 
        "ice_orchestrator.agent.base.AgentNode"
    )
    
    # Add more agents as they're created
    # global_agent_registry.register_agent(
    #     "research",
    #     "ice_orchestrator.agent.research.ResearchAgent"
    # ) 