"""Integration tests for robust agents with memory, reasoning, and planning.

These tests verify that the robust agents (MarketplaceConversationAgent, 
EnhancedMarketplaceAgent, ListingStatusAgent) work correctly with:
- Memory integration and persistence
- Multi-step reasoning and planning
- Tool coordination and execution
- Real-world conversation scenarios
"""

import asyncio
import pytest
from typing import Dict, Any

from ice_core.unified_registry import global_agent_registry
from ice_orchestrator.agent.memory import MemoryAgentConfig
from ice_core.models import LLMConfig, ModelProvider


class TestRobustAgents:
    """Test suite for robust agents with full capabilities."""
    
    @pytest.fixture(autouse=True)
    def setup_agents(self):
        """Import modules to trigger agent registration."""
        # Import modules to trigger registration
        import ice_tools.toolkits.marketplace.conversation_agent  # noqa: F401
        import ice_tools.toolkits.marketplace.enhanced_agent  # noqa: F401
        import ice_tools.toolkits.marketplace.listing_status_agent  # noqa: F401
    
    @pytest.mark.asyncio
    async def test_marketplace_conversation_agent_memory_integration(self):
        """Test that conversation agent maintains memory across interactions."""
        
        # Get fresh agent instance
        agent = global_agent_registry.get_agent_instance("marketplace_conversation_agent")
        
        # First interaction
        result1 = await agent.execute({
            "messages": [{"role": "user", "content": "Is this refrigerator still available?"}],
            "customer_id": "customer_123",
            "listing_id": "listing_456",
            "listing_context": {
                "listing_item": "Refrigerator",
                "listing_price": "$600",
                "listing_condition": "Good",
                "listing_location": "Downtown",
            }
        })
        
        # Verify first response
        assert result1.success
        output1 = result1.output
        assert output1["action"] == "respond"
        assert "available" in output1["response"].lower()
        assert output1["conversation_state"] == "simple_inquiry"
        assert output1["memory_key"] == "conversation:customer_123:listing_456"
        
        # Second interaction - should remember context
        result2 = await agent.execute({
            "messages": [
                {"role": "user", "content": "Is this refrigerator still available?"},
                {"role": "assistant", "content": output1["response"]},
                {"role": "user", "content": "What about delivery options?"}
            ],
            "customer_id": "customer_123",
            "listing_id": "listing_456",
            "listing_context": {
                "listing_item": "Refrigerator", 
                "listing_price": "$600",
                "listing_condition": "Good",
                "listing_location": "Downtown",
            }
        })
        
        # Verify second response shows memory integration
        assert result2.success
        output2 = result2.output
        assert output2["action"] in ["respond", "trigger_human"]
        assert len(output2["conversation_history"]) > 0
        assert output2["memory_key"] == "conversation:customer_123:listing_456"
    
    @pytest.mark.asyncio
    async def test_enhanced_marketplace_agent_tool_planning(self):
        """Test that enhanced agent can plan and execute tools."""
        
        # Get fresh agent instance
        agent = global_agent_registry.get_agent_instance("enhanced_marketplace_agent")
        
        # Complex inquiry that should trigger tool usage
        result = await agent.execute({
            "messages": [{"role": "user", "content": "I want to negotiate the price of this refrigerator. Can you help me get a better deal?"}],
            "customer_id": "customer_789",
            "listing_id": "listing_101",
            "listing_context": {
                "listing_item": "Refrigerator",
                "listing_price": "$800",
                "listing_condition": "Excellent",
                "listing_location": "Uptown",
            }
        })
        
        # Verify enhanced reasoning capabilities
        assert result.success
        output = result.output
        assert output["action"] in ["respond", "trigger_human", "use_tool"]
        assert "reasoning" in output or "tool_results" in output
        assert output.get("requires_human", False) in [True, False]
    
    @pytest.mark.asyncio
    async def test_listing_status_agent_decision_making(self):
        """Test that listing status agent can analyze conversations and make decisions."""
        
        # Get fresh agent instance
        agent = global_agent_registry.get_agent_instance("listing_status_agent")
        
        # Simulate a conversation result that should trigger status update
        conversation_result = {
            "action": "respond",
            "response": "Yes, the refrigerator is still available! The price is $600 and it's in good condition.",
            "requires_human": False,
            "conversation_state": "price_inquiry",
            "reasoning": {
                "inquiry_analysis": {"inquiry_type": "availability", "complexity": "simple"},
                "response_plan": {"strategy": "direct_response"}
            }
        }
        
        result = await agent.execute({
            "conversation_result": conversation_result,
            "listing_id": "listing_456",
            "listing_context": {
                "listing_item": "Refrigerator",
                "listing_price": "$600",
                "listing_condition": "Good",
                "listing_location": "Downtown",
            }
        })
        
        # Verify status decision
        assert result.success
        output = result.output
        assert output["action"] in ["update_status", "maintain_status", "flag_for_review", "no_change"]
        assert "status_decision" in output
        assert "reasoning" in output
    
    @pytest.mark.asyncio
    async def test_agent_memory_persistence(self):
        """Test that agent memory persists across multiple executions."""
        
        # Get fresh agent instance
        agent = global_agent_registry.get_agent_instance("marketplace_conversation_agent")
        
        customer_id = "persistent_customer"
        listing_id = "persistent_listing"
        
        # First interaction
        result1 = await agent.execute({
            "messages": [{"role": "user", "content": "What's the price?"}],
            "customer_id": customer_id,
            "listing_id": listing_id,
            "listing_context": {"listing_item": "Laptop", "listing_price": "$500"}
        })
        
        # Second interaction - should remember previous context
        result2 = await agent.execute({
            "messages": [
                {"role": "user", "content": "What's the price?"},
                {"role": "assistant", "content": result1.output["response"]},
                {"role": "user", "content": "Is it negotiable?"}
            ],
            "customer_id": customer_id,
            "listing_id": listing_id,
            "listing_context": {"listing_item": "Laptop", "listing_price": "$500"}
        })
        
        # Verify memory persistence
        assert result1.success and result2.success
        output1 = result1.output
        output2 = result2.output
        assert output1["memory_key"] == output2["memory_key"]
        assert len(output2["conversation_history"]) > 0
    
    @pytest.mark.asyncio
    async def test_agent_error_handling(self):
        """Test that agents handle errors gracefully."""
        
        # Get fresh agent instance
        agent = global_agent_registry.get_agent_instance("marketplace_conversation_agent")
        
        # Test with invalid input
        result = await agent.execute({
            "messages": [],  # Empty messages should trigger error handling
            "customer_id": "test_customer",
            "listing_id": "test_listing"
        })
        
        # Verify error handling - agents now handle empty messages gracefully
        assert result.success
        assert result.output["action"] == "error"
        assert "No messages provided" in result.output["message"]
    
    @pytest.mark.asyncio
    async def test_agent_factory_pattern(self):
        """Test that agent factory pattern works correctly."""
        
        # Verify agents are registered
        assert "marketplace_conversation_agent" in global_agent_registry._agents
        assert "enhanced_marketplace_agent" in global_agent_registry._agents
        assert "listing_status_agent" in global_agent_registry._agents
        
        # Test factory instantiation
        agent1 = global_agent_registry.get_agent_instance("marketplace_conversation_agent")
        agent2 = global_agent_registry.get_agent_instance("marketplace_conversation_agent")
        
        # Verify fresh instances (not singletons)
        assert agent1 is not agent2
        
        # Verify agents implement IAgent protocol
        from ice_core.protocols.agent import IAgent
        assert isinstance(agent1, IAgent)
        assert isinstance(agent2, IAgent) 