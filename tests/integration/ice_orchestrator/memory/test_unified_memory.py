"""Integration tests for UnifiedMemory system."""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from ice_orchestrator.memory import (
    UnifiedMemory, UnifiedMemoryConfig,
    EpisodicMemory, SemanticMemory, ProceduralMemory,
    WorkingMemory, MemoryConfig
)


class TestUnifiedMemory:
    """Test suite for unified memory system integration."""
    
    @pytest.fixture
    async def unified_memory(self):
        """Create fully configured unified memory."""
        config = UnifiedMemoryConfig(
            enable_working=True,
            enable_episodic=True,
            enable_semantic=True,
            enable_procedural=True,
            working_config=MemoryConfig(backend="memory", ttl_seconds=300),
            episodic_config=MemoryConfig(backend="memory", ttl_seconds=3600),
            semantic_config=MemoryConfig(backend="memory", enable_vector_search=True),
            procedural_config=MemoryConfig(backend="memory")
        )
        memory = UnifiedMemory(config)
        await memory.initialize()
        yield memory
        # Cleanup
        for mem_type in memory._memories.values():
            await mem_type.clear()
    
    @pytest.mark.asyncio
    async def test_initialization(self, unified_memory):
        """Test that all memory subsystems are initialized."""
        # Check all memory types are present
        assert "working" in unified_memory._memories
        assert "episodic" in unified_memory._memories
        assert "semantic" in unified_memory._memories
        assert "procedural" in unified_memory._memories
        
        # Check they're the right types
        assert isinstance(unified_memory._memories["working"], WorkingMemory)
        assert isinstance(unified_memory._memories["episodic"], EpisodicMemory)
        assert isinstance(unified_memory._memories["semantic"], SemanticMemory)
        assert isinstance(unified_memory._memories["procedural"], ProceduralMemory)
    
    @pytest.mark.asyncio
    async def test_key_routing(self, unified_memory):
        """Test that keys are routed to correct memory types."""
        # Store with different key patterns
        await unified_memory.store("work:current_task", "Processing order 123")
        await unified_memory.store("episode:conv_001", {"messages": ["Hello", "Hi"]})
        await unified_memory.store("fact:pricing_rule", "Items over $100 ship free")
        await unified_memory.store("procedure:greeting", {"name": "Greeting", "template": "Hello!"})
        
        # Retrieve and verify routing
        work_item = await unified_memory.retrieve("work:current_task")
        assert work_item is not None
        assert work_item.content == "Processing order 123"
        
        episode = await unified_memory.retrieve("episode:conv_001")
        assert episode is not None
        assert "messages" in episode.content
        
        fact = await unified_memory.retrieve("fact:pricing_rule")
        assert fact is not None
        
        procedure = await unified_memory.retrieve("procedure:greeting")
        assert procedure is not None
        assert procedure.content["name"] == "Greeting"
    
    @pytest.mark.asyncio
    async def test_memory_specific_operations(self, unified_memory):
        """Test memory-specific operations through unified interface."""
        # Working memory expiration
        await unified_memory.store(
            "work:temp_data",
            "Temporary",
            metadata={"ttl": 1}  # 1 second
        )
        
        # Should exist immediately
        assert await unified_memory.retrieve("work:temp_data") is not None
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        assert await unified_memory.retrieve("work:temp_data") is None
        
        # Episodic memory with participants
        await unified_memory.store(
            "episode:customer_chat",
            {"conversation": "Chat log"},
            metadata={
                "participants": ["customer_123"],
                "outcome": "sale"
            }
        )
        
        # Semantic memory with entities
        await unified_memory.store(
            "fact:laptop_info",
            "Dell XPS is a premium laptop",
            metadata={
                "entities": ["dell_xps", "laptop"],
                "relationships": [{"type": "is_a", "target": "laptop"}]
            }
        )
        
        # Procedural memory validation
        with pytest.raises(ValueError):  # Should validate procedure format
            await unified_memory.store(
                "procedure:invalid",
                "Not a valid procedure"  # Missing required structure
            )
    
    @pytest.mark.asyncio
    async def test_cross_memory_search(self, unified_memory):
        """Test searching across different memory types."""
        # Store related information in different memories
        
        # Episode about a laptop sale
        await unified_memory.store(
            "episode:laptop_sale_001",
            {
                "customer": "John Doe",
                "item": "Dell XPS 13",
                "messages": ["Is the laptop still available?", "Yes, it's available!"],
                "outcome": "sold"
            },
            metadata={
                "participants": ["customer_john"],
                "tags": ["laptop", "successful_sale"]
            }
        )
        
        # Fact about laptop pricing
        await unified_memory.store(
            "fact:laptop_pricing",
            {
                "rule": "Dell XPS typically sells for 70% of retail when used",
                "confidence": 0.85
            },
            metadata={
                "entities": ["dell_xps", "pricing"],
                "domain": "marketplace"
            }
        )
        
        # Procedure for laptop sales
        await unified_memory.store(
            "procedure:laptop_sale_process",
            {
                "name": "Laptop Sale Process",
                "steps": [
                    {"action": "verify_specs"},
                    {"action": "demonstrate_condition"},
                    {"action": "negotiate_price"}
                ]
            },
            metadata={
                "category": "sales_process",
                "contexts": ["laptop_inquiry"]
            }
        )
        
        # Search for "laptop" should find entries across memories
        laptop_results = await unified_memory.search("laptop")
        assert len(laptop_results) >= 3
        
        # Verify we got results from different memory types
        result_keys = [r.key for r in laptop_results]
        assert any(k.startswith("episode:") for k in result_keys)
        assert any(k.startswith("fact:") for k in result_keys)
        assert any(k.startswith("procedure:") for k in result_keys)
    
    @pytest.mark.asyncio
    async def test_agent_scenario(self, unified_memory):
        """Test a realistic agent scenario using all memory types."""
        # Agent handles a customer inquiry about a laptop
        
        # 1. Store current task in working memory
        await unified_memory.store(
            "work:current_customer",
            {
                "customer_id": "cust_456",
                "inquiry": "Interested in Dell XPS",
                "status": "active"
            }
        )
        
        # 2. Check episodic memory for past interactions
        await unified_memory.store(
            "episode:cust_456_history",
            {
                "previous_purchases": ["iPhone 12"],
                "preferences": "High-end electronics",
                "last_interaction": "2 weeks ago"
            },
            metadata={
                "participants": ["cust_456"],
                "outcome": "positive"
            }
        )
        
        # 3. Retrieve relevant facts from semantic memory
        await unified_memory.store(
            "fact:dell_xps_specs",
            {
                "processor": "Intel i7",
                "ram": "16GB",
                "price_new": 1299,
                "price_used": 900
            },
            metadata={
                "entities": ["dell_xps"],
                "confidence": 0.95
            }
        )
        
        # 4. Get applicable procedures
        await unified_memory.store(
            "procedure:premium_customer_approach",
            {
                "name": "Premium Customer Approach",
                "steps": [
                    {"action": "acknowledge_history", "template": "Welcome back! I see you purchased {previous_item}"},
                    {"action": "emphasize_quality", "template": "The Dell XPS matches your preference for premium electronics"},
                    {"action": "offer_loyalty_discount", "discount": 0.05}
                ],
                "applicable_when": {
                    "customer_history": "positive",
                    "item_category": "premium"
                }
            },
            metadata={
                "category": "customer_service",
                "success_rate": 0.85
            }
        )
        
        # Now simulate agent using all memories
        
        # Get current task
        current_task = await unified_memory.retrieve("work:current_customer")
        assert current_task.content["customer_id"] == "cust_456"
        
        # Get customer history
        history_results = await unified_memory.search(
            "cust_456",
            memory_type="episodic"
        )
        assert len(history_results) > 0
        assert history_results[0].content["previous_purchases"][0] == "iPhone 12"
        
        # Get product facts
        product_facts = await unified_memory.search(
            "dell_xps",
            memory_type="semantic"
        )
        assert len(product_facts) > 0
        
        # Find applicable procedures
        proc_context = {
            "customer_history": "positive",
            "item_category": "premium"
        }
        # Note: This would use the procedural memory's find_applicable_procedures
        # but we're testing through unified interface
        procedures = await unified_memory.search(
            "premium customer",
            memory_type="procedural"
        )
        assert len(procedures) > 0
    
    @pytest.mark.asyncio
    async def test_memory_persistence_scenario(self, unified_memory):
        """Test memory persistence across agent sessions."""
        # Simulate first agent session
        session_id = "session_001"
        
        # Agent learns from interaction
        await unified_memory.store(
            f"episode:{session_id}_interaction",
            {
                "customer": "Alice",
                "conversation": [
                    "I need a laptop for graphic design",
                    "I recommend the Dell XPS with upgraded GPU",
                    "That sounds perfect!"
                ],
                "outcome": "sale"
            },
            metadata={
                "participants": ["alice", "agent"],
                "tags": ["graphic_design", "successful_sale"]
            }
        )
        
        # Store learned fact
        await unified_memory.store(
            "fact:graphic_design_needs",
            {
                "requirement": "Customers mentioning graphic design need dedicated GPU",
                "confidence": 0.9
            },
            metadata={
                "entities": ["graphic_design", "gpu"],
                "source": "learned",
                "learned_from": session_id
            }
        )
        
        # Update procedure based on success
        await unified_memory.store(
            "procedure:design_laptop_recommendation",
            {
                "name": "Recommend Laptop for Designers",
                "steps": [
                    {"action": "identify_design_needs"},
                    {"action": "emphasize_gpu", "template": "For design work, you'll want our model with dedicated GPU"},
                    {"action": "suggest_ram_upgrade"}
                ]
            },
            metadata={
                "category": "recommendation",
                "contexts": ["design_inquiry"],
                "success_rate": 0.9
            }
        )
        
        # Simulate new session - memories persist
        new_customer_context = {
            "inquiry": "I do video editing and 3D modeling"
        }
        
        # Agent should find relevant past knowledge
        design_facts = await unified_memory.search(
            "design",
            memory_type="semantic"
        )
        assert len(design_facts) > 0
        assert "gpu" in design_facts[0].metadata["entities"]
        
        # Should find successful procedure
        design_procedures = await unified_memory.search(
            "design",
            memory_type="procedural"
        )
        assert len(design_procedures) > 0
        assert design_procedures[0].metadata["success_rate"] == 0.9
    
    @pytest.mark.asyncio
    async def test_memory_cleanup(self, unified_memory):
        """Test memory cleanup and management."""
        # Fill different memories
        for i in range(10):
            await unified_memory.store(f"work:task_{i}", f"Task {i}")
            await unified_memory.store(
                f"episode:event_{i}",
                f"Event {i}",
                metadata={"timestamp": datetime.now().isoformat()}
            )
            await unified_memory.store(
                f"fact:rule_{i}",
                f"Rule {i}",
                metadata={"confidence": 0.5 + i * 0.05}
            )
        
        # Clear working memory only
        cleared = await unified_memory.clear("work:")
        assert cleared >= 10
        
        # Verify working memory cleared but others remain
        assert await unified_memory.retrieve("work:task_0") is None
        assert await unified_memory.retrieve("episode:event_0") is not None
        assert await unified_memory.retrieve("fact:rule_0") is not None
        
        # Clear all memories
        total_cleared = await unified_memory.clear()
        assert total_cleared >= 20  # Remaining episodes and facts
    
    @pytest.mark.asyncio
    async def test_memory_type_routing(self, unified_memory):
        """Test explicit memory type specification."""
        # Store without prefix but specify type
        await unified_memory.store(
            "my_work_item",
            "Work data",
            memory_type="working"
        )
        
        await unified_memory.store(
            "my_episode",
            {"event": "Something happened"},
            memory_type="episodic"
        )
        
        # Retrieve with type hint
        work = await unified_memory.retrieve("my_work_item", memory_type="working")
        assert work is not None
        
        episode = await unified_memory.retrieve("my_episode", memory_type="episodic")
        assert episode is not None
        
        # Wrong type should return None
        assert await unified_memory.retrieve("my_work_item", memory_type="episodic") is None
    
    @pytest.mark.asyncio
    async def test_concurrent_memory_access(self, unified_memory):
        """Test concurrent access to different memory types."""
        async def store_in_memory(mem_type: str, count: int):
            tasks = []
            for i in range(count):
                key = f"{mem_type}:concurrent_{i}"
                task = unified_memory.store(key, f"Data {i}")
                tasks.append(task)
            await asyncio.gather(*tasks)
        
        # Concurrent stores to all memory types
        await asyncio.gather(
            store_in_memory("work", 10),
            store_in_memory("episode", 10),
            store_in_memory("fact", 10),
            store_in_memory("procedure", 10)
        )
        
        # Verify all stored
        for mem_type in ["work", "episode", "fact", "procedure"]:
            for i in range(10):
                key = f"{mem_type}:concurrent_{i}"
                assert await unified_memory.retrieve(key) is not None
    
    @pytest.mark.asyncio
    async def test_memory_statistics(self, unified_memory):
        """Test gathering statistics across memory types."""
        # Populate memories
        for i in range(5):
            await unified_memory.store(f"work:item_{i}", f"Work {i}")
            await unified_memory.store(
                f"episode:event_{i}",
                f"Event {i}",
                metadata={"outcome": "success" if i % 2 == 0 else "failure"}
            )
            await unified_memory.store(
                f"fact:fact_{i}",
                f"Fact {i}",
                metadata={"confidence": 0.7 + i * 0.05}
            )
        
        # Get statistics
        stats = await unified_memory.get_statistics()
        
        assert stats["working"]["count"] == 5
        assert stats["episodic"]["count"] == 5
        assert stats["semantic"]["count"] == 5
        
        # Memory-specific stats
        assert "success_count" in stats["episodic"]
        assert "avg_confidence" in stats["semantic"]


class TestMemoryAgentIntegration:
    """Test memory integration with agent workflows."""
    
    @pytest.mark.asyncio
    async def test_learning_agent_workflow(self):
        """Test an agent that learns and improves over time."""
        # Create unified memory
        memory = UnifiedMemory(UnifiedMemoryConfig(
            enable_working=True,
            enable_episodic=True,
            enable_semantic=True,
            enable_procedural=True
        ))
        await memory.initialize()
        
        # Simulate multiple customer interactions
        interactions = [
            {
                "customer": "cust_001",
                "item": "laptop",
                "initial_offer": 700,
                "final_price": 850,
                "outcome": "sale"
            },
            {
                "customer": "cust_002",
                "item": "laptop",
                "initial_offer": 600,
                "final_price": 0,
                "outcome": "abandoned"
            },
            {
                "customer": "cust_003",
                "item": "laptop",
                "initial_offer": 800,
                "final_price": 825,
                "outcome": "sale"
            }
        ]
        
        for i, interaction in enumerate(interactions):
            # Working memory for current negotiation
            await memory.store(
                f"work:current_negotiation",
                interaction,
                metadata={"started": datetime.now().isoformat()}
            )
            
            # Store episode
            await memory.store(
                f"episode:negotiation_{i}",
                interaction,
                metadata={
                    "participants": [interaction["customer"]],
                    "outcome": interaction["outcome"],
                    "tags": ["negotiation", interaction["item"]]
                }
            )
            
            # Learn from outcome
            if interaction["outcome"] == "sale":
                # Successful negotiation - store as fact
                margin = (interaction["final_price"] - interaction["initial_offer"]) / interaction["initial_offer"]
                await memory.store(
                    f"fact:negotiation_success_{i}",
                    {
                        "initial_offer_ratio": interaction["initial_offer"] / 1000,  # Assuming $1000 list
                        "counter_offer_margin": margin,
                        "result": "success"
                    },
                    metadata={
                        "entities": ["negotiation", "laptop"],
                        "confidence": 0.8
                    }
                )
        
        # After interactions, agent analyzes patterns
        
        # Get all negotiation episodes
        negotiations = await memory.search("negotiation", memory_type="episodic")
        
        # Calculate success rate
        successful = [n for n in negotiations if n.metadata.get("outcome") == "sale"]
        success_rate = len(successful) / len(negotiations) if negotiations else 0
        
        # Store learned procedure
        await memory.store(
            "procedure:laptop_negotiation_improved",
            {
                "name": "Improved Laptop Negotiation",
                "steps": [
                    {"action": "evaluate_offer", "min_acceptable": 0.7},  # 70% of list
                    {"action": "counter_offer", "margin": 0.15},  # 15% above initial
                    {"action": "max_discount", "limit": 0.2}  # 20% max discount
                ],
                "learned_from": f"{len(negotiations)} negotiations",
                "success_rate": success_rate
            },
            metadata={
                "category": "negotiation",
                "contexts": ["laptop_offer"],
                "success_rate": success_rate
            }
        )
        
        # Verify learning
        learned_procedure = await memory.retrieve("procedure:laptop_negotiation_improved")
        assert learned_procedure is not None
        assert learned_procedure.content["success_rate"] > 0.6
        
        # Clean up
        await memory.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 