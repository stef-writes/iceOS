"""Initialize the global agent registry with built-in agents."""

from ice_sdk.unified_registry import global_agent_registry


def initialize_agent_registry():
    """Register all built-in agents with their import paths."""
    
    # Register marketplace agents [[memory:4056190]]
    global_agent_registry.register(
        "marketplace_listing_agent",
        "ice_sdk.agents.marketplace.listing_agent.ListingAgent"
    )
    
    # Add more agents here as they are created
    # global_agent_registry.register(
    #     "research_agent",
    #     "ice_sdk.agents.research.research_agent.ResearchAgent"
    # ) 