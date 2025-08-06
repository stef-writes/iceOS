"""Demo of the Facebook Marketplace conversation agent with memory and human triggers.

This demo shows how the marketplace conversation agent:
1. Handles simple availability questions automatically
2. Triggers human intervention for complex inquiries
3. Uses built-in memory to maintain conversation context
4. Updates listing status when conversations lead to sales
"""

import asyncio

from ice_core.unified_registry import global_agent_registry

# Import the marketplace toolkit to register everything
from src.ice_tools.toolkits.marketplace import MarketplaceToolkit


async def demo_simple_inquiry():
    """Demo handling a simple availability question."""
    print("🤖 **Demo: Simple Availability Question**")
    print("-" * 50)

    # Get the conversation agent
    agent_class = global_agent_registry.get_agent_class(
        "marketplace_conversation_agent"
    )
    agent = agent_class()

    # Simple availability question
    messages = [{"role": "user", "content": "Is this refrigerator still available?"}]

    result = await agent.run(
        messages=messages, customer_id="customer_123", listing_id="refrigerator_456"
    )

    print(f"Customer: {messages[0]['content']}")
    print(f"Agent Action: {result['action']}")
    print(f"Response: {result.get('response', 'N/A')}")
    print(f"Requires Human: {result['requires_human']}")
    print(f"Memory Key: {result.get('memory_key', 'N/A')}")
    print()


async def demo_complex_inquiry():
    """Demo triggering human intervention for complex inquiry."""
    print("🤖 **Demo: Complex Inquiry - Human Trigger**")
    print("-" * 50)

    # Get the conversation agent
    agent_class = global_agent_registry.get_agent_class(
        "marketplace_conversation_agent"
    )
    agent = agent_class()

    # Complex inquiry that should trigger human
    messages = [
        {"role": "user", "content": "What's your best price for this refrigerator?"}
    ]

    result = await agent.run(
        messages=messages, customer_id="customer_123", listing_id="refrigerator_456"
    )

    print(f"Customer: {messages[0]['content']}")
    print(f"Agent Action: {result['action']}")
    print(f"Reason: {result.get('reason', 'N/A')}")
    print(f"Requires Human: {result['requires_human']}")
    print(f"Conversation State: {result['conversation_state']}")
    print()


async def demo_listing_status_update():
    """Demo updating listing status when conversation leads to sale."""
    print("🤖 **Demo: Listing Status Update**")
    print("-" * 50)

    # Get the listing status agent
    agent_class = global_agent_registry.get_agent_class("listing_status_agent")
    agent = agent_class()

    # Simulate conversation that led to a sale
    conversation_result = {
        "action": "sale_completed",
        "customer_id": "customer_123",
        "listing_id": "refrigerator_456",
    }

    result = await agent.run(
        conversation_result=conversation_result, listing_id="refrigerator_456"
    )

    print(f"Conversation Result: {conversation_result['action']}")
    print(f"Agent Action: {result['action']}")
    print(f"New Status: {result.get('new_status', 'N/A')}")
    print(f"Reason: {result.get('reason', 'N/A')}")
    print(f"Success: {result['success']}")
    print()


async def main():
    """Run all demos."""
    print("🚀 **Facebook Marketplace Conversation Agent Demo**")
    print("=" * 60)
    print()

    # Register the marketplace toolkit
    toolkit = MarketplaceToolkit()
    print(
        f"✅ Registered {len(toolkit.get_tools())} tools and {len(toolkit.get_agents())} agents"
    )
    print()

    # Run demos
    await demo_simple_inquiry()
    await demo_complex_inquiry()
    await demo_listing_status_update()

    print("🎉 **Demo Complete!**")
    print()
    print("Key Features Demonstrated:")
    print("✅ Built-in memory for conversation context")
    print("✅ Automatic handling of simple availability questions")
    print("✅ Human intervention triggers for complex inquiries")
    print("✅ Listing status updates based on conversation outcomes")
    print("✅ Clean agent architecture in ice_tools")


if __name__ == "__main__":
    asyncio.run(main())
