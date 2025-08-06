"""Multi-turn marketplace conversation demo with real OpenAI API calls.

This demo shows how the marketplace conversation agent handles:
1. Multi-turn conversations with memory
2. Real OpenAI API calls for responses
3. Context-aware responses based on conversation history
4. Human intervention triggers for complex inquiries
"""

import asyncio
import os

# Direct imports to avoid recursive import issues
# from src.ice_tools.toolkits.marketplace.conversation_agent import MarketplaceConversationAgent
from ice_core.unified_registry import global_agent_registry

# Import agents to trigger registration


async def simulate_multi_turn_conversation():
    """Simulate a multi-turn conversation with the marketplace agent."""
    print("🤖 **Multi-Turn Marketplace Conversation Demo**")
    print("=" * 60)
    print()

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Using fallback responses.")
        print("   Set OPENAI_API_KEY to test with real API calls.")
        print()

    # Create agent using the registry (which will call the factory)
    agent = global_agent_registry.get_agent_instance(
        global_agent_registry.get_agent_import_path("marketplace_conversation_agent")
    )

    # Listing context
    listing_context = {
        "listing_item": "Stainless Steel Refrigerator",
        "listing_price": "$600",
        "listing_condition": "Good - minor scratches on side",
        "listing_location": "Downtown, pickup available",
    }

    # Simulate conversation turns
    conversation_turns = [
        "Is this refrigerator still available?",
        "What's the condition like?",
        "Can you deliver it?",
        "What's your best price?",
        "Is it energy efficient?",
    ]

    messages = []

    for i, message in enumerate(conversation_turns, 1):
        print(f"🔄 **Turn {i}**")
        print(f"Customer: {message}")
        print("-" * 40)

        # Add message to conversation
        messages.append({"role": "user", "content": message})

        # Get agent response
        result = await agent.run(
            messages=messages,
            customer_id="customer_123",
            listing_id="refrigerator_456",
            listing_context=listing_context,
        )

        # Display response
        if result["action"] == "respond":
            print(f"🤖 Agent: {result['response']}")
            print(f"   Status: {result['conversation_state']}")
            print(f"   Memory Key: {result.get('memory_key', 'N/A')}")
        else:
            print(f"🤖 Agent: {result.get('acknowledgment', 'Acknowledging...')}")
            print(f"   Action: {result['action']}")
            print(f"   Reason: {result['reason']}")
            print(f"   Status: {result['conversation_state']}")
            print("   ⚠️  Human intervention required!")

        print()

        # Show conversation history if available
        if "conversation_history" in result and result["conversation_history"]:
            print("📝 **Conversation History:**")
            for entry in result["conversation_history"][-3:]:  # Show last 3 entries
                if isinstance(entry, dict) and "message" in entry:
                    role = entry.get("role", "user").title()
                    print(f"   {role}: {entry['message']}")
            print()

    print("🎉 **Multi-turn conversation complete!**")
    print()
    print("Key Features Demonstrated:")
    print("✅ Real OpenAI API calls (when API key is set)")
    print("✅ Multi-turn conversation memory")
    print("✅ Context-aware responses")
    print("✅ Automatic handling of simple questions")
    print("✅ Human intervention for complex inquiries")
    print("✅ Conversation history tracking")


async def test_conversation_memory():
    """Test conversation memory across multiple sessions."""
    print("🧠 **Conversation Memory Test**")
    print("=" * 50)
    print()

    agent = global_agent_registry.get_agent_instance(
        global_agent_registry.get_agent_import_path("marketplace_conversation_agent")
    )

    # First conversation
    print("📅 **Session 1**")
    messages1 = [{"role": "user", "content": "Is the refrigerator available?"}]

    result1 = await agent.run(
        messages=messages1, customer_id="customer_123", listing_id="refrigerator_456"
    )

    print(f"Customer: {messages1[0]['content']}")
    print(f"Agent: {result1['response']}")
    print()

    # Second conversation (same customer, different time)
    print("📅 **Session 2** (later)")
    messages2 = [{"role": "user", "content": "What about delivery options?"}]

    result2 = await agent.run(
        messages=messages2,
        customer_id="customer_123",  # Same customer
        listing_id="refrigerator_456",  # Same listing
    )

    print(f"Customer: {messages2[0]['content']}")
    print(f"Agent: {result2.get('acknowledgment', result2.get('response', 'N/A'))}")
    print(f"Action: {result2['action']}")
    print()

    print("✅ Memory test complete!")


async def main():
    """Run all demos."""
    print("🚀 **Facebook Marketplace Multi-Turn Conversation Demo**")
    print("=" * 70)
    print()

    # Run multi-turn conversation demo
    await simulate_multi_turn_conversation()
    print()

    # Run memory test
    await test_conversation_memory()
    print()

    print("🎯 **Demo Summary:**")
    print("• Real OpenAI API integration")
    print("• Multi-turn conversation handling")
    print("• Persistent conversation memory")
    print("• Context-aware responses")
    print("• Human intervention triggers")
    print("• Clean agent architecture")


if __name__ == "__main__":
    asyncio.run(main())
