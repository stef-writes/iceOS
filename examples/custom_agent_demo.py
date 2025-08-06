#!/usr/bin/env python3
"""Demo of customizing agents with enhanced memory, tools, and reasoning."""

import asyncio
import sys
from typing import Any, Dict, List

# Add src to path
sys.path.insert(0, 'src')

from ice_core.unified_registry import global_agent_registry
from ice_core.memory import UnifiedMemoryConfig, EpisodicMemory, SemanticMemory
from ice_tools.toolkits.marketplace.conversation_agent import create_marketplace_conversation_agent
from ice_tools.toolkits.marketplace.listing_status_agent import create_listing_status_agent

# Register agents
global_agent_registry.register_agent(
    "marketplace_conversation_agent", 
    "ice_tools.toolkits.marketplace.conversation_agent:create_marketplace_conversation_agent",
)
global_agent_registry.register_agent(
    "listing_status_agent", 
    "ice_tools.toolkits.marketplace.listing_status_agent:create_listing_status_agent",
)

async def demo_custom_memory():
    """Demo customizing memory configuration."""
    print("🧠 **Custom Memory Configuration Demo**")
    print("=" * 50)
    
    # Create custom memory config
    custom_memory_config = UnifiedMemoryConfig(
        backend="memory",  # Use in-memory for demo
        enable_vector_search=True,
        enable_working=True,
        enable_episodic=True,
        enable_semantic=True,
        enable_procedural=True,
        domains=["marketplace", "pricing", "inventory"]
    )
    
    # Create agent with custom memory
    agent = global_agent_registry.get_agent_instance(
        global_agent_registry.get_agent_import_path("marketplace_conversation_agent")
    )
    
    # Store some custom memories
    await agent.memory.store(
        key="customer_preferences:user_123",
        content={
            "prefers_delivery": True,
            "budget_range": "$500-$800",
            "location": "Downtown",
            "response_style": "formal"
        }
    )
    
    await agent.memory.store(
        key="product_knowledge:refrigerators",
        content={
            "energy_efficiency_ratings": ["A++", "A+", "A"],
            "common_features": ["frost_free", "multi_zone", "smart_connectivity"],
            "price_ranges": {
                "basic": "$300-$500",
                "mid_range": "$500-$800", 
                "premium": "$800-$1500"
            }
        }
    )
    
    print("✅ Custom memory configured and populated")
    return agent

async def demo_enhanced_reasoning():
    """Demo enhanced reasoning capabilities."""
    print("\n🤔 **Enhanced Reasoning Demo**")
    print("=" * 40)
    
    agent = await demo_custom_memory()
    
    # Test with enhanced reasoning
    messages = [
        {"role": "user", "content": "What's the best refrigerator for someone who wants energy efficiency and delivery?"}
    ]
    
    result = await agent.execute({
        "messages": messages,
        "customer_id": "user_123",
        "listing_id": "refrigerator_456",
        "listing_context": {
            "listing_item": "Samsung Energy Star Refrigerator",
            "listing_price": "$750",
            "listing_condition": "New",
            "listing_location": "Downtown",
            "features": ["A++ energy rating", "frost_free", "multi_zone"]
        }
    })
    
    print(f"Enhanced reasoning result: {result.output}")
    return result

async def demo_tool_integration():
    """Demo integrating tools with agents."""
    print("\n🔧 **Tool Integration Demo**")
    print("=" * 35)
    
    # Create agent that can use tools
    agent = global_agent_registry.get_agent_instance(
        global_agent_registry.get_agent_import_path("marketplace_conversation_agent")
    )
    
    # Simulate tool availability (in real workflow, tools are injected by orchestrator)
    agent.tools = [
        {
            "name": "price_calculator",
            "description": "Calculate pricing with discounts and taxes",
            "parameters": {"base_price": "float", "discount_percent": "float"}
        },
        {
            "name": "delivery_scheduler", 
            "description": "Check delivery availability and schedule",
            "parameters": {"zip_code": "string", "preferred_date": "string"}
        },
        {
            "name": "inventory_checker",
            "description": "Check current inventory levels",
            "parameters": {"product_id": "string"}
        }
    ]
    
    # Test with tool-aware reasoning
    messages = [
        {"role": "user", "content": "Can you check if this refrigerator is in stock and calculate the total price with delivery?"}
    ]
    
    result = await agent.execute({
        "messages": messages,
        "customer_id": "user_456",
        "listing_id": "refrigerator_789",
        "listing_context": {
            "listing_item": "LG Smart Refrigerator",
            "listing_price": "$850",
            "listing_condition": "New",
            "listing_location": "Downtown",
            "product_id": "LG-FRIDGE-001"
        }
    })
    
    print(f"Tool-integrated reasoning result: {result.output}")
    return result

async def demo_multi_agent_workflow():
    """Demo multiple agents working together."""
    print("\n🤝 **Multi-Agent Workflow Demo**")
    print("=" * 40)
    
    # Get both agents
    conversation_agent = global_agent_registry.get_agent_instance(
        global_agent_registry.get_agent_import_path("marketplace_conversation_agent")
    )
    
    status_agent = global_agent_registry.get_agent_instance(
        global_agent_registry.get_agent_import_path("listing_status_agent")
    )
    
    # Simulate conversation leading to sale
    conversation_result = await conversation_agent.execute({
        "messages": [
            {"role": "user", "content": "I want to buy this refrigerator. What's the final price with delivery?"}
        ],
        "customer_id": "buyer_123",
        "listing_id": "refrigerator_final",
        "listing_context": {
            "listing_item": "Whirlpool French Door Refrigerator",
            "listing_price": "$1200",
            "listing_condition": "Excellent",
            "listing_location": "Downtown"
        }
    })
    
    print(f"Conversation agent result: {conversation_result.output}")
    
    # Status agent processes the conversation outcome
    status_result = await status_agent.execute({
        "conversation_result": conversation_result.output,
        "listing_id": "refrigerator_final"
    })
    
    print(f"Status agent result: {status_result.output}")
    
    return conversation_result, status_result

async def main():
    """Run all customization demos."""
    print("🚀 **Agent Customization Demo**")
    print("=" * 60)
    print()
    
    try:
        # Demo 1: Custom memory
        await demo_enhanced_reasoning()
        
        # Demo 2: Tool integration  
        await demo_tool_integration()
        
        # Demo 3: Multi-agent workflow
        await demo_multi_agent_workflow()
        
        print("\n🎉 **All customization demos completed!**")
        print("\nKey Features Demonstrated:")
        print("✅ Custom memory configuration")
        print("✅ Enhanced reasoning with context")
        print("✅ Tool integration capabilities")
        print("✅ Multi-agent coordination")
        print("✅ Persistent memory across interactions")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 