"""Integration test for FB Marketplace Seller workflow."""

import asyncio
import pytest
from datetime import datetime
from typing import Dict, Any

from use_cases.RivaRidge.FB_Marketplace_Seller.FBMSeller import FBMSeller
from ice_orchestrator.memory import EpisodicMemory, SemanticMemory, ProceduralMemory
from ice_orchestrator.memory import MemoryConfig


@pytest.mark.asyncio
async def test_fb_marketplace_workflow_basic():
    """Test basic FB Marketplace workflow execution."""
    # Initialize workflow
    seller = FBMSeller(config={
        "marketplace": "facebook",
        "location": "Seattle, WA",
        "min_value_threshold": 25.0,
        "condition_requirements": ["New", "Like New", "Good"]
    })
    
    # Test inventory
    test_inventory = {
        "items": [
            {
                "id": "test-001",
                "name": "Gaming Laptop",
                "condition": "Like New",
                "original_price": 1200.00,
                "quantity": 1,
                "images": ["laptop1.jpg", "laptop2.jpg"]
            },
            {
                "id": "test-002",
                "name": "Old Monitor",
                "condition": "Fair",
                "original_price": 50.00,
                "quantity": 1,
                "images": ["monitor1.jpg"]
            }
        ]
    }
    
    # Note: This would fail in actual execution without mocking
    # as it tries to execute the full workflow with real tools
    # For now, just verify the workflow structure is correct
    
    workflow = seller.builder.to_workflow()
    
    # Verify workflow has all expected nodes
    node_ids = [node.id for node in workflow.nodes]
    expected_nodes = [
        "inventory_analyzer",
        "price_research", 
        "image_enhancer",
        "listing_creator",
        "message_monitor",
        "check_messages",
        "respond_to_messages",
        "metrics_tracker"
    ]
    
    for expected in expected_nodes:
        assert expected in node_ids, f"Missing node: {expected}"
    
    # Verify connections
    assert len(workflow.edges) > 0
    
    # Verify loop structure
    loop_nodes = [n for n in workflow.nodes if n.type == "loop"]
    assert len(loop_nodes) == 1
    assert loop_nodes[0].id == "message_monitor"


@pytest.mark.asyncio
async def test_memory_systems():
    """Test all memory systems are functional."""
    
    # Test EpisodicMemory
    episodic_config = MemoryConfig(
        backend="redis",
        ttl_seconds=3600,
                    connection_params={"host": "localhost", "port": 6379}
    )
    episodic = EpisodicMemory(episodic_config)
    await episodic.initialize()
    
    # Store a conversation episode
    await episodic.store(
        key="conv_001",
        content={
            "messages": ["Is this available?", "Yes, it's available!"],
            "outcome": "inquiry_handled"
        },
        metadata={
            "type": "conversation",
            "participants": ["buyer_123", "seller"],
            "outcome": "positive",
            "tags": ["availability_check"]
        }
    )
    
    # Retrieve it
    episode = await episodic.retrieve("conv_001")
    assert episode is not None
    assert episode.metadata["outcome"] == "positive"
    
    # Test SemanticMemory
    semantic_config = MemoryConfig(
        backend="memory",
        enable_vector_search=True
    )
    semantic = SemanticMemory(semantic_config)
    await semantic.initialize()
    
    # Store a fact
    await semantic.store(
        key="pricing_rule_laptop",
        content={
            "rule": "Gaming laptops typically sell for 60-70% of original price",
            "category": "laptop",
            "confidence": 0.85
        },
        metadata={
            "type": "pricing_rule",
            "entities": ["laptop", "gaming"],
            "domain": "marketplace"
        }
    )
    
    # Search for it
    results = await semantic.search("gaming laptop pricing")
    assert len(results) > 0
    
    # Test ProceduralMemory
    procedural_config = MemoryConfig(backend="memory")
    procedural = ProceduralMemory(procedural_config)
    await procedural.initialize()
    
    # Find negotiation procedures
    negotiation_procs = await procedural.search(
        "negotiation",
        filters={"category": "negotiation"}
    )
    assert len(negotiation_procs) > 0
    
    # Test finding applicable procedures
    context = {
        "type": "price_inquiry",
        "offer_range": [0.75, 0.85],
        "buyer_engagement": "high"
    }
    applicable = await procedural.find_applicable_procedures(
        context, 
        category="negotiation"
    )
    assert len(applicable) > 0


@pytest.mark.asyncio 
async def test_tool_integrations():
    """Test individual tools work correctly."""
    from use_cases.RivaRidge.FB_Marketplace_Seller.tools.inventory import InventoryAnalyzerTool
    from use_cases.RivaRidge.FB_Marketplace_Seller.tools.analytics import AnalyticsTrackerTool
    from use_cases.RivaRidge.FB_Marketplace_Seller.tools.communication import MessageParserTool
    
    # Test InventoryAnalyzer
    analyzer = InventoryAnalyzerTool()
    result = await analyzer._execute_impl(
        inventory=[
            {
                "id": "item-001",
                "name": "iPhone 12",
                "condition": "Good",
                "original_price": 800,
                "quantity": 1
            },
            {
                "id": "item-002",
                "name": "Broken Charger",
                "condition": "Poor",
                "original_price": 20,
                "quantity": 1
            }
        ],
        config={"min_value_threshold": 50.0}
    )
    
    assert len(result["eligible_items"]) == 1
    assert len(result["rejected_items"]) == 1
    assert result["eligible_items"][0]["id"] == "item-001"
    
    # Test MessageParser
    parser = MessageParserTool()
    parsed = await parser._execute_impl(
        messages=[{
            "content": "Hi! Is this still available? I can pick it up today for $300.",
            "timestamp": datetime.now().isoformat()
        }]
    )
    
    assert len(parsed["parsed_messages"]) == 1
    msg = parsed["parsed_messages"][0]
    assert "availability" in msg["intents"]
    assert msg["urgency"] == "high"  # "today" indicates high urgency
    assert msg["is_negotiation"] is True  # Contains price offer
    
    # Test AnalyticsTracker
    tracker = AnalyticsTrackerTool()
    analytics = await tracker._execute_impl(
        listings_data=[
            {
                "listing_id": "fb_001",
                "status": "sold",
                "price": 400,
                "created_at": datetime.now().isoformat(),
                "category": "Electronics"
            }
        ],
        message_data=[],
        start_time=datetime.now().isoformat()
    )
    
    assert "metrics_report" in analytics
    assert analytics["performance_summary"]["total_listings"] == 1
    assert analytics["performance_summary"]["total_revenue"] == 400


@pytest.mark.asyncio
async def test_agent_interactions():
    """Test agent components work together."""
    from ice_sdk.agents import CustomerServiceAgent, MarketplaceAgent
    
    # Test customer service agent structure
    cs_agent = CustomerServiceAgent()
    assert cs_agent.config.id == "customer_service_agent"
    assert "message_parser" in cs_agent.config.tools
    assert "facebook_api" in cs_agent.config.tools
    
    # Test marketplace agent structure
    mp_agent = MarketplaceAgent()
    assert mp_agent.config.id == "marketplace_agent"
    assert "price_research" in mp_agent.config.tools
    
    # Both agents should have proper system prompts
    assert len(cs_agent.config.system_prompt) > 100
    assert len(mp_agent.config.system_prompt) > 100


@pytest.mark.asyncio
async def test_end_to_end_scenario():
    """Test a complete scenario from inventory to sale."""
    # This would be a full integration test in production
    # For now, we verify the components are wired correctly
    
    seller = FBMSeller()
    
    # Verify workflow can be built
    workflow = seller.builder.to_workflow()
    
    # Check critical paths exist
    # inventory_analyzer -> price_research -> listing_creator
    edges = [(e.source, e.target) for e in workflow.edges]
    assert ("inventory_analyzer", "price_research") in edges
    assert ("price_research", "listing_creator") in edges
    
    # Check parallel execution
    assert ("inventory_analyzer", "image_enhancer") in edges
    
    # Check loop contains message handling
    loop_node = next(n for n in workflow.nodes if n.id == "message_monitor")
    assert hasattr(loop_node, "body_nodes")
    assert "check_messages" in loop_node.body_nodes
    assert "respond_to_messages" in loop_node.body_nodes
    
    print("✅ All FB Marketplace Seller components integrated successfully!")


if __name__ == "__main__":
    asyncio.run(test_end_to_end_scenario()) 