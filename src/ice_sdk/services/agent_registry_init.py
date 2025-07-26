"""Agent registry initialization."""

from ice_sdk.unified_registry import global_agent_registry


def initialize_agent_registry():
    """Register core agents in the global registry."""
    # Register Memory Agent
    global_agent_registry.register_agent(
        "memory",
        "ice_sdk.agents.memory_agent.MemoryAgent"
    )
    
    # Add more agents as they're created
    # global_agent_registry.register_agent(
    #     "research",
    #     "ice_sdk.agents.research_agent.ResearchAgent"
    # ) 