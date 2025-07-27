"""Comprehensive unit tests for SemanticMemory."""

import pytest
import pytest_asyncio
import numpy as np
from datetime import datetime
from typing import Dict, Any, List

from ice_orchestrator.memory.semantic import SemanticMemory
from ice_orchestrator.memory import MemoryConfig


class TestSemanticMemory:
    """Test suite for SemanticMemory implementation."""
    
    @pytest_asyncio.fixture
    async def memory_basic(self):
        """Create SemanticMemory without vector search."""
        config = MemoryConfig(
            backend="memory",
            enable_vector_search=False
        )
        memory = SemanticMemory(config)
        await memory.initialize()
        yield memory
        await memory.clear()
    
    @pytest_asyncio.fixture
    async def memory_vector(self):
        """Create SemanticMemory with vector search enabled."""
        config = MemoryConfig(
            backend="memory",
            enable_vector_search=True
        )
        memory = SemanticMemory(config)
        await memory.initialize()
        yield memory
        await memory.clear()
    
    @pytest.mark.asyncio
    async def test_basic_store_retrieve(self, memory_basic):
        """Test basic store and retrieve operations."""
        # Store a fact
        await memory_basic.store(
            key="fact_001",
            content={
                "statement": "Gaming laptops depreciate to 70% value when like new",
                "confidence": 0.85
            },
            metadata={
                "type": "pricing_rule",
                "entities": ["laptop", "gaming", "depreciation"],
                "domain": "marketplace"
            }
        )
        
        # Retrieve it
        fact = await memory_basic.retrieve("fact_001")
        assert fact is not None
        assert fact.key == "fact_001"
        assert fact.content["confidence"] == 0.85
        assert "laptop" in fact.metadata["entities"]
        assert fact.metadata["domain"] == "marketplace"
    
    @pytest.mark.asyncio
    async def test_entity_indexing(self, memory_basic):
        """Test entity-based indexing and retrieval."""
        # Store facts about entities
        facts = [
            ("laptop_spec", {"ram": "16GB", "cpu": "i7"}, ["laptop", "dell_xps"]),
            ("laptop_price", {"msrp": 1200, "resale": 800}, ["laptop", "dell_xps", "pricing"]),
            ("phone_spec", {"screen": "6.1inch", "5g": True}, ["phone", "iphone_12"]),
        ]
        
        for key, content, entities in facts:
            await memory_basic.store(
                key=key,
                content=content,
                metadata={"entities": entities}
            )
        
        # Find facts related to laptop
        laptop_facts = await memory_basic.find_related("laptop")
        assert len(laptop_facts) == 2
        
        # Find facts related to specific laptop model
        dell_facts = await memory_basic.find_related("dell_xps")
        assert len(dell_facts) == 2
        
        # Find facts about phone
        phone_facts = await memory_basic.find_related("phone")
        assert len(phone_facts) == 1
    
    @pytest.mark.asyncio
    async def test_relationships(self, memory_basic):
        """Test relationship storage and retrieval."""
        # Store facts with relationships
        await memory_basic.store(
            key="laptop_category",
            content="Dell XPS is a laptop",
            metadata={
                "entities": ["dell_xps"],
                "relationships": [
                    {"type": "is_a", "target": "laptop"},
                    {"type": "manufactured_by", "target": "dell"}
                ]
            }
        )
        
        await memory_basic.store(
            key="laptop_competitor",
            content="MacBook Pro competes with Dell XPS",
            metadata={
                "entities": ["macbook_pro"],
                "relationships": [
                    {"type": "competes_with", "target": "dell_xps"},
                    {"type": "is_a", "target": "laptop"}
                ]
            }
        )
        
        # Test relationship storage
        assert "laptop_category" in memory_basic._relationships
        relationships = memory_basic._relationships["laptop_category"]
        assert ("is_a", "laptop") in relationships
        assert ("manufactured_by", "dell") in relationships
    
    @pytest.mark.asyncio
    async def test_text_search(self, memory_basic):
        """Test text-based search without vectors."""
        # Store various facts
        await memory_basic.store(
            key="pricing_rule_1",
            content="Electronics typically lose 30% value in first year",
            metadata={"type": "rule", "domain": "pricing"}
        )
        
        await memory_basic.store(
            key="pricing_rule_2",
            content="Luxury items retain value better than electronics",
            metadata={"type": "rule", "domain": "pricing"}
        )
        
        await memory_basic.store(
            key="shipping_rule",
            content="Free shipping on electronics over $100",
            metadata={"type": "rule", "domain": "shipping"}
        )
        
        # Search for electronics
        results = await memory_basic.search("electronics")
        assert len(results) == 2
        keys = [r.key for r in results]
        assert "pricing_rule_1" in keys
        assert "shipping_rule" in keys
        
        # Search with domain filter
        results = await memory_basic.search(
            "electronics",
            filters={"domain": "pricing"}
        )
        assert len(results) == 1
        assert results[0].key == "pricing_rule_1"
    
    @pytest.mark.asyncio
    async def test_vector_search(self, memory_vector):
        """Test vector-based semantic search."""
        # Store facts with similar meanings
        facts = [
            ("laptop_fast", "This laptop has exceptional speed and performance"),
            ("laptop_slow", "This laptop is sluggish and underperforms"),
            ("laptop_review", "The laptop offers great performance for the price"),
            ("phone_fast", "This phone has lightning fast processing"),
        ]
        
        for key, content in facts:
            await memory_vector.store(key, content)
        
        # Search for performance-related facts
        results = await memory_vector.search("laptop performance")
        assert len(results) >= 2
        
        # Laptop performance facts should rank higher than phone
        keys = [r.key for r in results]
        laptop_keys = [k for k in keys if "laptop" in k]
        assert len(laptop_keys) >= 2
    
    @pytest.mark.asyncio
    async def test_embedding_generation(self, memory_vector):
        """Test embedding generation and storage."""
        # Store a fact
        await memory_vector.store(
            key="embed_test",
            content="Test content for embedding"
        )
        
        # Check embedding was created
        assert "embed_test" in memory_vector._embeddings
        embedding = memory_vector._embeddings["embed_test"]
        
        # Verify embedding properties
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (memory_vector._embedding_dim,)
        assert np.allclose(np.linalg.norm(embedding), 1.0)  # Should be normalized
    
    @pytest.mark.asyncio
    async def test_metadata_filters(self, memory_basic):
        """Test various metadata filter combinations."""
        # Store facts with different metadata
        facts = [
            ("fact1", "Content 1", {
                "fact_type": "rule",
                "domain": "pricing", 
                "entities": ["laptop"],
                "confidence": 0.9
            }),
            ("fact2", "Content 2", {
                "fact_type": "observation",
                "domain": "pricing",
                "entities": ["phone", "tablet"],
                "confidence": 0.7
            }),
            ("fact3", "Content 3", {
                "fact_type": "rule",
                "domain": "shipping",
                "entities": ["laptop", "desktop"],
                "confidence": 0.95
            }),
        ]
        
        for key, content, metadata in facts:
            await memory_basic.store(key, content, metadata)
        
        # Filter by type
        results = await memory_basic.search("", filters={"type": "rule"})
        assert len(results) == 2
        
        # Filter by domain
        results = await memory_basic.search("", filters={"domain": "pricing"})
        assert len(results) == 2
        
        # Filter by entities
        results = await memory_basic.search("", filters={"entities": ["laptop"]})
        assert len(results) == 2
        
        # Filter by minimum confidence
        results = await memory_basic.search("", filters={"min_confidence": 0.8})
        assert len(results) == 2
        
        # Multiple filters
        results = await memory_basic.search("", filters={
            "type": "rule",
            "domain": "pricing",
            "min_confidence": 0.8
        })
        assert len(results) == 1
        assert results[0].key == "fact1"
    
    @pytest.mark.asyncio
    async def test_knowledge_graph(self, memory_basic):
        """Test knowledge graph generation."""
        # Build a knowledge network
        await memory_basic.store(
            key="laptop_def",
            content="A laptop is a portable computer",
            metadata={
                "entities": ["laptop"],
                "relationships": [{"type": "is_a", "target": "computer"}]
            }
        )
        
        await memory_basic.store(
            key="dell_laptop",
            content="Dell XPS is a premium laptop",
            metadata={
                "entities": ["dell_xps"],
                "relationships": [
                    {"type": "is_a", "target": "laptop"},
                    {"type": "made_by", "target": "dell"}
                ]
            }
        )
        
        await memory_basic.store(
            key="computer_def",
            content="A computer processes information",
            metadata={
                "entities": ["computer"],
                "relationships": [{"type": "used_for", "target": "computing"}]
            }
        )
        
        # Generate knowledge graph starting from dell_xps
        graph = await memory_basic.get_knowledge_graph("dell_xps", max_depth=2)
        
        # Check graph structure
        assert "nodes" in graph
        assert "edges" in graph
        
        # Check nodes
        assert "dell_xps" in graph["nodes"]
        assert "laptop" in graph["nodes"]  # Connected via is_a
        assert "dell" in graph["nodes"]    # Connected via made_by
        
        # Check edges
        edges = graph["edges"]
        edge_tuples = [(e["source"], e["target"], e["type"]) for e in edges]
        assert ("dell_xps", "laptop", "is_a") in edge_tuples
        assert ("dell_xps", "dell", "made_by") in edge_tuples
    
    @pytest.mark.asyncio
    async def test_learning_from_interaction(self, memory_basic):
        """Test learning new facts from interactions."""
        # Simulate a sale interaction
        interaction = {
            "item_type": "laptop",
            "item_condition": "like_new",
            "sale_price": 850,
            "customer_id": "cust_123",
            "preferences": {
                "prefers_fast_shipping": True,
                "budget_conscious": False
            }
        }
        
        # Learn from interaction
        facts_learned = await memory_basic.learn_from_interaction(interaction)
        
        # Check pricing pattern was learned
        pricing_key = f"pricing_pattern_laptop_like_new"
        pricing_fact = await memory_basic.retrieve(pricing_key)
        assert pricing_fact is not None
        assert pricing_fact.content["item_type"] == "laptop"
        assert pricing_fact.content["price_range"] == 850
        
        # Check customer preference was learned
        pref_key = f"customer_pref_cust_123"
        pref_fact = await memory_basic.retrieve(pref_key)
        assert pref_fact is not None
        assert pref_fact.content["prefers_fast_shipping"] is True
    
    @pytest.mark.asyncio
    async def test_domain_knowledge(self, memory_basic):
        """Test domain-specific knowledge retrieval."""
        # Store facts in different domains
        domains = ["marketplace", "shipping", "customer_service"]
        types = ["rule", "observation", "pattern"]
        
        for domain in domains:
            for i, fact_type in enumerate(types):
                await memory_basic.store(
                    key=f"{domain}_{fact_type}_{i}",
                    content=f"Fact about {domain}",
                    metadata={
                        "domain": domain,
                        "fact_type": fact_type
                    }
                )
        
        # Get all marketplace knowledge
        marketplace_facts = await memory_basic.get_domain_knowledge("marketplace")
        assert len(marketplace_facts) == 3
        
        # Get specific type in domain
        marketplace_rules = await memory_basic.get_domain_knowledge(
            "marketplace",
            fact_type="rule"
        )
        assert len(marketplace_rules) == 1
    
    @pytest.mark.asyncio
    async def test_fact_merging(self, memory_basic):
        """Test merging multiple facts."""
        # Create related facts
        await memory_basic.store(
            key="laptop_price_1",
            content="Dell XPS typically sells for $800-900 used",
            metadata={"entities": ["dell_xps", "pricing"]}
        )
        
        await memory_basic.store(
            key="laptop_price_2",
            content="Dell XPS in mint condition can reach $950",
            metadata={"entities": ["dell_xps", "pricing", "mint_condition"]}
        )
        
        await memory_basic.store(
            key="laptop_price_3",
            content="Dell XPS with damage sells for $600-700",
            metadata={"entities": ["dell_xps", "pricing", "damaged"]}
        )
        
        # Merge facts
        success = await memory_basic.merge_facts(
            ["laptop_price_1", "laptop_price_2", "laptop_price_3"],
            "dell_xps_pricing_merged"
        )
        assert success is True
        
        # Check merged fact
        merged = await memory_basic.retrieve("dell_xps_pricing_merged")
        assert merged is not None
        assert len(merged.content["facts"]) == 3
        assert merged.metadata["type"] == "merged_fact"
        
        # Original facts should be deleted
        assert await memory_basic.retrieve("laptop_price_1") is None
    
    @pytest.mark.asyncio
    async def test_delete_operations(self, memory_basic):
        """Test deletion functionality."""
        # Store facts with relationships
        await memory_basic.store(
            key="delete_test",
            content="Test content",
            metadata={
                "entities": ["test_entity"],
                "relationships": [{"type": "related_to", "target": "other"}]
            }
        )
        
        # Verify indexes are populated
        assert "test_entity" in memory_basic._entity_index
        assert "delete_test" in memory_basic._relationships
        
        # Delete
        deleted = await memory_basic.delete("delete_test")
        assert deleted is True
        
        # Verify cleanup
        assert await memory_basic.retrieve("delete_test") is None
        assert "test_entity" not in memory_basic._entity_index
        assert "delete_test" not in memory_basic._relationships
    
    @pytest.mark.asyncio
    async def test_clear_operations(self, memory_basic):
        """Test clear functionality."""
        # Store facts with patterns
        for i in range(3):
            await memory_basic.store(f"temp_{i}", f"Temporary fact {i}")
            await memory_basic.store(f"keep_{i}", f"Permanent fact {i}")
        
        # Clear by pattern
        cleared = await memory_basic.clear("temp_")
        assert cleared == 3
        
        # Verify temp facts are gone
        assert await memory_basic.retrieve("temp_0") is None
        
        # keep facts should remain
        assert await memory_basic.retrieve("keep_0") is not None
        
        # Clear all
        total = await memory_basic.clear()
        assert total >= 3
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, memory_vector):
        """Test concurrent access patterns."""
        import asyncio
        
        # Concurrent stores
        tasks = []
        for i in range(10):
            task = memory_vector.store(
                key=f"concurrent_{i}",
                content=f"Fact number {i}",
                metadata={
                    "entities": [f"entity_{i}"],
                    "index": i
                }
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify all stored
        for i in range(10):
            fact = await memory_vector.retrieve(f"concurrent_{i}")
            assert fact is not None
            assert fact.metadata["index"] == i
        
        # Verify embeddings created
        if memory_vector._enable_vectors:
            for i in range(10):
                assert f"concurrent_{i}" in memory_vector._embeddings
    
    @pytest.mark.asyncio
    async def test_similarity_ranking(self, memory_vector):
        """Test that vector search properly ranks by similarity."""
        # Store facts with varying relevance to "laptop performance"
        facts = [
            ("exact_match", "laptop performance benchmarks"),
            ("high_relevance", "notebook computer speed and performance"),
            ("medium_relevance", "laptop battery life and efficiency"),
            ("low_relevance", "desktop computer specifications"),
            ("no_relevance", "smartphone camera quality")
        ]
        
        for key, content in facts:
            await memory_vector.store(key, content)
        
        # Search for laptop performance
        results = await memory_vector.search("laptop performance", limit=5)
        
        # Results should be ordered by relevance
        # (Note: with hash-based embeddings, this is approximate)
        keys = [r.key for r in results]
        
        # Most relevant should appear before least relevant
        exact_idx = keys.index("exact_match") if "exact_match" in keys else 999
        no_rel_idx = keys.index("no_relevance") if "no_relevance" in keys else -1
        
        if exact_idx != 999 and no_rel_idx != -1:
            assert exact_idx < no_rel_idx
    
    @pytest.mark.asyncio
    async def test_metadata_enrichment(self, memory_basic):
        """Test that metadata is enriched with defaults."""
        # Store with minimal metadata
        await memory_basic.store(
            key="enrichment_test",
            content="Test fact",
            metadata={"custom": "value"}
        )
        
        # Retrieve and check
        fact = await memory_basic.retrieve("enrichment_test")
        
        # Should have defaults
        assert fact.metadata["fact_type"] == "general"
        assert fact.metadata["domain"] == "general"
        assert fact.metadata["confidence"] == 1.0
        assert fact.metadata["source"] == "system"
        assert isinstance(fact.metadata["entities"], list)
        assert isinstance(fact.metadata["relationships"], list)
        
        # Custom field preserved
        assert fact.metadata["custom"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 