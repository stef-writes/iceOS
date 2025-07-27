"""Comprehensive unit tests for EpisodicMemory."""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
import redis

from ice_orchestrator.memory.episodic import EpisodicMemory
from ice_orchestrator.memory import MemoryConfig


class TestEpisodicMemory:
    """Test suite for EpisodicMemory implementation."""
    
    @pytest_asyncio.fixture
    async def memory_redis(self):
        """Create EpisodicMemory with Redis backend."""
        config = MemoryConfig(
            backend="redis",
            ttl_seconds=3600,
            connection_params={
                "host": "localhost",
                "port": 6379,
                "db": 15  # Use separate DB for tests
            }
        )
        memory = EpisodicMemory(config)
        await memory.initialize()
        
        # Clear any existing data
        await memory.clear()
        
        yield memory
        
        # Cleanup
        await memory.clear()
    
    @pytest_asyncio.fixture
    async def memory_fallback(self):
        """Create EpisodicMemory with in-memory fallback."""
        config = MemoryConfig(
            backend="redis",
            connection_params={
                "host": "invalid_host",  # Force fallback
                "port": 9999
            }
        )
        memory = EpisodicMemory(config)
        await memory.initialize()
        
        yield memory
        
        await memory.clear()
    
    @pytest.mark.asyncio
    async def test_basic_store_retrieve(self, memory_fallback):
        """Test basic store and retrieve operations."""
        # Store an episode
        await memory_fallback.store(
            key="episode_001",
            content={
                "conversation": ["Hello", "Hi there!"],
                "duration": 120
            },
            metadata={
                "type": "greeting",
                "participants": ["user_123", "agent"],
                "outcome": "positive"
            }
        )
        
        # Retrieve it
        episode = await memory_fallback.retrieve("episode_001")
        assert episode is not None
        assert episode.key == "episode_001"
        assert episode.content["duration"] == 120
        assert episode.metadata["type"] == "greeting"
        assert "user_123" in episode.metadata["participants"]
    
    @pytest.mark.asyncio
    async def test_nonexistent_key(self, memory_fallback):
        """Test retrieving non-existent key."""
        result = await memory_fallback.retrieve("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_operations(self, memory_fallback):
        """Test delete functionality."""
        # Store multiple episodes
        for i in range(3):
            await memory_fallback.store(
                key=f"delete_test_{i}",
                content={"index": i},
                metadata={"type": "test"}
            )
        
        # Delete one
        deleted = await memory_fallback.delete("delete_test_1")
        assert deleted is True
        
        # Verify it's gone
        assert await memory_fallback.retrieve("delete_test_1") is None
        
        # Others should still exist
        assert await memory_fallback.retrieve("delete_test_0") is not None
        assert await memory_fallback.retrieve("delete_test_2") is not None
        
        # Delete non-existent
        deleted = await memory_fallback.delete("nonexistent")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_search_by_content(self, memory_fallback):
        """Test searching by content."""
        # Store episodes with different content
        episodes = [
            ("ep1", {"message": "Looking for a laptop"}, {"type": "inquiry"}),
            ("ep2", {"message": "Need help with shipping"}, {"type": "support"}),
            ("ep3", {"message": "Laptop arrived damaged"}, {"type": "complaint"})
        ]
        
        for key, content, metadata in episodes:
            await memory_fallback.store(key, content, metadata)
        
        # Search for "laptop"
        results = await memory_fallback.search("laptop")
        assert len(results) == 2
        keys = [r.key for r in results]
        assert "ep1" in keys
        assert "ep3" in keys
        
        # Case insensitive search
        results = await memory_fallback.search("LAPTOP")
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, memory_fallback):
        """Test searching with metadata filters."""
        # Store episodes with various metadata
        episodes = [
            ("ep1", "Content 1", {
                "type": "conversation",
                "participant": "user_123",
                "outcome": "sale",
                "tags": ["electronics", "urgent"]
            }),
            ("ep2", "Content 2", {
                "type": "conversation", 
                "participant": "user_456",
                "outcome": "inquiry",
                "tags": ["furniture"]
            }),
            ("ep3", "Content 3", {
                "type": "support",
                "participant": "user_123",
                "outcome": "resolved",
                "tags": ["electronics", "warranty"]
            })
        ]
        
        for key, content, metadata in episodes:
            await memory_fallback.store(key, content, metadata)
        
        # Filter by type
        results = await memory_fallback.search("", filters={"type": "conversation"})
        assert len(results) == 2
        
        # Filter by participant
        results = await memory_fallback.search("", filters={"participant": "user_123"})
        assert len(results) == 2
        
        # Filter by outcome
        results = await memory_fallback.search("", filters={"outcome": "sale"})
        assert len(results) == 1
        assert results[0].key == "ep1"
        
        # Filter by tags
        results = await memory_fallback.search("", filters={"tags": ["electronics"]})
        assert len(results) == 2
        
        # Multiple filters
        results = await memory_fallback.search("", filters={
            "type": "conversation",
            "participant": "user_123"
        })
        assert len(results) == 1
        assert results[0].key == "ep1"
    
    @pytest.mark.asyncio
    async def test_clear_operations(self, memory_fallback):
        """Test clear functionality."""
        # Store episodes with patterns
        for i in range(5):
            await memory_fallback.store(f"test_{i}", f"content_{i}")
            await memory_fallback.store(f"keep_{i}", f"content_{i}")
        
        # Clear by pattern
        cleared = await memory_fallback.clear("test_")
        assert cleared == 5
        
        # Verify test_ episodes are gone
        assert await memory_fallback.retrieve("test_0") is None
        
        # keep_ episodes should remain
        assert await memory_fallback.retrieve("keep_0") is not None
        
        # Clear all
        cleared = await memory_fallback.clear()
        assert cleared >= 5  # At least the keep_ episodes
        
        # Everything should be gone
        assert await memory_fallback.retrieve("keep_0") is None
    
    @pytest.mark.asyncio
    async def test_list_keys(self, memory_fallback):
        """Test listing keys."""
        # Store some episodes
        keys_stored = []
        for i in range(15):
            key = f"list_test_{i:02d}"
            keys_stored.append(key)
            await memory_fallback.store(key, f"content_{i}")
        
        # List all keys
        keys = await memory_fallback.list_keys()
        assert len(keys) >= 15
        for key in keys_stored:
            assert key in keys
        
        # List with pattern
        keys = await memory_fallback.list_keys(pattern="list_test_0")
        matching = [k for k in keys if k.startswith("list_test_0")]
        assert len(matching) >= 10  # list_test_00 through list_test_09
        
        # List with limit
        keys = await memory_fallback.list_keys(limit=5)
        assert len(keys) <= 5
    
    @pytest.mark.asyncio
    async def test_conversation_history(self, memory_fallback):
        """Test conversation history retrieval."""
        # Create conversation episodes
        participant = "customer_789"
        
        for i in range(5):
            await memory_fallback.store(
                key=f"conv_{i}",
                content={
                    "messages": [f"Message {i}"],
                    "timestamp": (datetime.now() - timedelta(hours=i)).isoformat()
                },
                metadata={
                    "type": "conversation",
                    "participants": [participant, "agent"],
                    "outcome": "ongoing"
                }
            )
        
        # Get conversation history
        history = await memory_fallback.get_conversation_history(participant)
        assert len(history) == 5
        
        # Should be sorted by timestamp (most recent first)
        for i in range(1, len(history)):
            assert history[i-1].timestamp >= history[i].timestamp
    
    @pytest.mark.asyncio
    async def test_recent_episodes(self, memory_fallback):
        """Test retrieving recent episodes."""
        # Create episodes at different times
        now = datetime.now()
        
        # Old episode (25 hours ago)
        old_episode = EpisodicMemory(memory_fallback.config)
        old_episode._memory_store = memory_fallback._memory_store  # Share storage
        old_entry = old_episode._memory_store["old"] = type('Entry', (), {
            'timestamp': now - timedelta(hours=25),
            'metadata': {"episode_type": "conversation"},
            'content': "old content"
        })()
        
        # Recent episodes
        for i in range(3):
            await memory_fallback.store(
                key=f"recent_{i}",
                content=f"Recent content {i}",
                metadata={
                    "type": "conversation",
                    "timestamp_offset": i  # For testing
                }
            )
        
        # Get episodes from last 24 hours
        recent = await memory_fallback.get_recent_episodes(hours=24)
        assert len(recent) == 3
        
        # Get episodes of specific type
        recent_convos = await memory_fallback.get_recent_episodes(
            hours=24, 
            episode_type="conversation"
        )
        assert len(recent_convos) == 3
    
    @pytest.mark.asyncio
    async def test_pattern_analysis(self, memory_fallback):
        """Test pattern analysis functionality."""
        # Create episodes with various outcomes
        participant = "user_analysis"
        
        outcomes = ["sale", "sale", "inquiry", "sale", "abandoned", "inquiry"]
        sentiments = ["positive", "positive", "neutral", "positive", "negative", "neutral"]
        tags_list = [
            ["electronics", "urgent"],
            ["electronics", "discount"],
            ["furniture"],
            ["electronics"],
            ["electronics", "complaint"],
            ["books"]
        ]
        
        for i, (outcome, sentiment, tags) in enumerate(zip(outcomes, sentiments, tags_list)):
            await memory_fallback.store(
                key=f"analysis_{i}",
                content=f"Episode {i}",
                metadata={
                    "type": "conversation",
                    "participants": [participant],
                    "outcome": outcome,
                    "sentiment": sentiment,
                    "tags": tags
                }
            )
        
        # Analyze patterns
        analysis = await memory_fallback.analyze_patterns(participant=participant)
        
        assert analysis["total_episodes"] == 6
        
        # Check outcome distribution
        assert analysis["patterns"]["outcomes"]["sale"] == 3
        assert analysis["patterns"]["outcomes"]["inquiry"] == 2
        assert analysis["patterns"]["outcomes"]["abandoned"] == 1
        
        # Check sentiment distribution
        assert analysis["patterns"]["sentiments"]["positive"] == 3
        assert analysis["patterns"]["sentiments"]["neutral"] == 2
        assert analysis["patterns"]["sentiments"]["negative"] == 1
        
        # Check top tags
        top_tags = analysis["patterns"]["top_tags"]
        assert ("electronics", 4) in top_tags
        
        # Check insights
        assert len(analysis["insights"]) > 0
        assert any("Success rate:" in insight for insight in analysis["insights"])
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, memory_fallback):
        """Test concurrent access patterns."""
        # Concurrent stores
        tasks = []
        for i in range(10):
            task = memory_fallback.store(
                key=f"concurrent_{i}",
                content=f"Content {i}",
                metadata={"index": i}
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify all stored
        for i in range(10):
            episode = await memory_fallback.retrieve(f"concurrent_{i}")
            assert episode is not None
            assert episode.metadata["index"] == i
        
        # Concurrent searches
        search_tasks = []
        for _ in range(5):
            task = memory_fallback.search("Content")
            search_tasks.append(task)
        
        results = await asyncio.gather(*search_tasks)
        for result in results:
            assert len(result) == 10
    
    @pytest.mark.asyncio
    async def test_metadata_enrichment(self, memory_fallback):
        """Test that metadata is properly enriched during storage."""
        # Store with minimal metadata
        await memory_fallback.store(
            key="enrichment_test",
            content="Test content",
            metadata={"custom_field": "custom_value"}
        )
        
        # Retrieve and check enrichment
        episode = await memory_fallback.retrieve("enrichment_test")
        
        # Should have default fields added
        assert "episode_type" in episode.metadata
        assert episode.metadata["episode_type"] == "conversation"
        assert "participants" in episode.metadata
        assert "outcome" in episode.metadata
        assert "sentiment" in episode.metadata
        assert "tags" in episode.metadata
        
        # Custom field should be preserved
        assert episode.metadata["custom_field"] == "custom_value"
    
    @pytest.mark.asyncio
    async def test_indexing_functionality(self, memory_redis):
        """Test Redis-specific indexing features."""
        # Skip if Redis not available
        if not memory_redis._redis:
            pytest.skip("Redis not available")
        
        # Store episodes with various attributes
        await memory_redis.store(
            key="idx_test_1",
            content="Content 1",
            metadata={
                "type": "sale",
                "participants": ["user_001", "agent"],
                "tags": ["electronics", "laptop"],
                "outcome": "success"
            }
        )
        
        await memory_redis.store(
            key="idx_test_2",
            content="Content 2",
            metadata={
                "type": "inquiry",
                "participants": ["user_002", "agent"],
                "tags": ["electronics", "phone"],
                "outcome": "pending"
            }
        )
        
        # Check indexes exist in Redis
        type_members = memory_redis._redis.smembers(f"{memory_redis._index_prefix}type:sale")
        assert "idx_test_1" in type_members
        
        participant_members = memory_redis._redis.smembers(
            f"{memory_redis._index_prefix}participant:user_001"
        )
        assert "idx_test_1" in participant_members
        
        tag_members = memory_redis._redis.smembers(
            f"{memory_redis._index_prefix}tag:electronics"
        )
        assert len(tag_members) == 2
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, memory_redis):
        """Test TTL expiration in Redis."""
        # Skip if Redis not available
        if not memory_redis._redis:
            pytest.skip("Redis not available")
        
        # Create memory with short TTL
        short_ttl_config = MemoryConfig(
            backend="redis",
            ttl_seconds=2,  # 2 seconds
            connection_params={
                "host": "localhost",
                "port": 6379,
                "db": 15
            }
        )
        short_memory = EpisodicMemory(short_ttl_config)
        await short_memory.initialize()
        
        # Store episode
        await short_memory.store(
            key="ttl_test",
            content="Temporary content"
        )
        
        # Should exist immediately
        assert await short_memory.retrieve("ttl_test") is not None
        
        # Wait for expiration
        await asyncio.sleep(3)
        
        # Should be gone
        assert await short_memory.retrieve("ttl_test") is None
    
    @pytest.mark.asyncio
    async def test_error_handling(self, memory_fallback):
        """Test error handling in various scenarios."""
        # Store with None key should handle gracefully
        with pytest.raises(Exception):
            await memory_fallback.store(None, "content")
        
        # Store with invalid metadata types
        await memory_fallback.store(
            key="error_test",
            content="content",
            metadata={"tags": "not_a_list"}  # Should be list
        )
        
        # Should still be retrievable
        episode = await memory_fallback.retrieve("error_test")
        assert episode is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 