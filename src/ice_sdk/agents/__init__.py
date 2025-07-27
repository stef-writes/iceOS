"""SDK Agents module."""

from ice_sdk.agents.marketplace_agent import MarketplaceAgent, create_marketplace_agent
from ice_sdk.agents.customer_service import CustomerServiceAgent, create_customer_service_agent

# Register agents with the global registry
from ice_core.unified_registry import global_agent_registry

# Register marketplace agent
global_agent_registry["marketplace_agent"] = "ice_sdk.agents.marketplace_agent"
# Register customer service agent
global_agent_registry["customer_service"] = "ice_sdk.agents.customer_service"

__all__ = [
    "MarketplaceAgent",
    "create_marketplace_agent",
    "CustomerServiceAgent",
    "create_customer_service_agent"
]
