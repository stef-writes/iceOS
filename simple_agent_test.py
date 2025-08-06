#!/usr/bin/env python3
"""Simple test for agent factory pattern."""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, 'src')

# Direct imports to avoid recursive import issues
from ice_core.unified_registry import global_agent_registry
from ice_tools.toolkits.marketplace.conversation_agent import create_marketplace_conversation_agent
from ice_tools.toolkits.marketplace.listing_status_agent import create_listing_status_agent

# Manual registration
print("🔧 Manually registering agents...")
global_agent_registry.register_agent(
    "marketplace_conversation_agent", 
    "ice_tools.toolkits.marketplace.conversation_agent:create_marketplace_conversation_agent",
)
global_agent_registry.register_agent(
    "listing_status_agent", 
    "ice_tools.toolkits.marketplace.listing_status_agent:create_listing_status_agent",
)
print(f"✅ Registered agents: {list(global_agent_registry._agents.keys())}")

async def test_conversation_agent():
    """Test the conversation agent."""
    print("\n🤖 Testing conversation agent...")
    
    # Get fresh agent instance via factory
    agent = global_agent_registry.get_agent_instance(
        global_agent_registry.get_agent_import_path("marketplace_conversation_agent")
    )
    
    # Test with a simple message
    messages = [{"role": "user", "content": "Is this refrigerator still available?"}]
    
    result = await agent.execute({
        "messages": messages,
        "customer_id": "test_customer",
        "listing_id": "test_listing",
        "listing_context": {
            "listing_item": "Refrigerator",
            "listing_price": "$600",
            "listing_condition": "Good",
            "listing_location": "Downtown"
        }
    })
    
    print(f"✅ Agent response: {result}")
    return result

async def main():
    """Run the test."""
    print("🚀 Testing agent factory pattern...")
    
    try:
        result = await test_conversation_agent()
        print(f"\n🎉 Success! Agent executed with result: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 