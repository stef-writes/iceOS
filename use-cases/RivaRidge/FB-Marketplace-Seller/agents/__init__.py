"""Agents for Facebook Marketplace automation.

Note: Agents in iceOS are referenced by package string, not imported directly.
The actual agent implementations should be in ice_sdk.agents module.

Available agents:
- marketplace_agent: Creates optimized marketplace listings
- customer_service: Handles customer interactions (TBD)
"""

# Agent registration happens in ice_sdk.agents.__init__.py
# Usage in workflows:
# builder.add_agent(
#     node_id="my_agent",
#     package="ice_sdk.agents.marketplace_agent",
#     tools=["tool1", "tool2"]
# ) 