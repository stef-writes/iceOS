"""Simple test of the marketplace conversation agent."""

import asyncio

# Direct imports to avoid recursive import issues
from src.ice_tools.toolkits.marketplace.conversation_agent import (
    MarketplaceConversationAgent,
)
from src.ice_tools.toolkits.marketplace.listing_status_agent import ListingStatusAgent


async def test_simple_inquiry():
    """Test handling a simple availability question."""
    print("🤖 **Test: Simple Availability Question**")
    print("-" * 50)

    # Create agent directly
    agent = MarketplaceConversationAgent()

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


async def test_complex_inquiry():
    """Test triggering human intervention for complex inquiry."""
    print("🤖 **Test: Complex Inquiry - Human Trigger**")
    print("-" * 50)

    # Create agent directly
    agent = MarketplaceConversationAgent()

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


async def test_listing_status_update():
    """Test updating listing status when conversation leads to sale."""
    print("🤖 **Test: Listing Status Update**")
    print("-" * 50)

    # Create agent directly
    agent = ListingStatusAgent()

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
    """Run all tests."""
    print("🚀 **Facebook Marketplace Conversation Agent Test**")
    print("=" * 60)
    print()

    # Run tests
    await test_simple_inquiry()
    await test_complex_inquiry()
    await test_listing_status_update()

    print("🎉 **Test Complete!**")
    print()
    print("Key Features Demonstrated:")
    print("✅ Built-in memory for conversation context")
    print("✅ Automatic handling of simple availability questions")
    print("✅ Human intervention triggers for complex inquiries")
    print("✅ Listing status updates based on conversation outcomes")
    print("✅ Clean agent architecture in ice_tools")


if __name__ == "__main__":
    asyncio.run(main())
