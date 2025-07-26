"""Unit tests for working memory implementation."""

import asyncio
import pytest
from datetime import datetime, timedelta

from ice_sdk.memory import WorkingMemory, MemoryConfig, MemoryEntry


@pytest.mark.asyncio
async def test_working_memory_basic_operations():
    """Test basic store/retrieve operations."""
    config = MemoryConfig(backend="memory", ttl_seconds=60)
    
    async with WorkingMemory(config) as memory:
        # Store and retrieve
        await memory.store("test_key", "test_value", {"type": "test"})
        
        entry = await memory.retrieve("test_key")
        assert entry is not None
        assert entry.content == "test_value"
        assert entry.metadata["type"] == "test"
        assert entry.access_count == 1
        
        # Retrieve again - access count should increment
        entry = await memory.retrieve("test_key")
        assert entry.access_count == 2
        
        # Non-existent key
        entry = await memory.retrieve("missing_key")
        assert entry is None


@pytest.mark.asyncio
async def test_working_memory_expiration():
    """Test TTL expiration."""
    config = MemoryConfig(backend="memory", ttl_seconds=1)
    
    async with WorkingMemory(config) as memory:
        await memory.store("expire_test", "value")
        
        # Should exist immediately
        entry = await memory.retrieve("expire_test")
        assert entry is not None
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        entry = await memory.retrieve("expire_test")
        assert entry is None


@pytest.mark.asyncio
async def test_working_memory_size_limit():
    """Test max entries enforcement."""
    config = MemoryConfig(backend="memory", max_entries=3)
    
    async with WorkingMemory(config) as memory:
        # Store 4 entries
        for i in range(4):
            await memory.store(f"key_{i}", f"value_{i}")
            
        # First entry should be evicted
        assert await memory.retrieve("key_0") is None
        assert await memory.retrieve("key_1") is not None
        assert await memory.retrieve("key_2") is not None
        assert await memory.retrieve("key_3") is not None


@pytest.mark.asyncio
async def test_working_memory_search():
    """Test search functionality."""
    async with WorkingMemory() as memory:
        # Store test data
        await memory.store("user:123", {"name": "John", "role": "buyer"}, {"type": "user"})
        await memory.store("user:456", {"name": "Jane", "role": "seller"}, {"type": "user"})
        await memory.store("product:789", {"name": "Laptop", "price": 999}, {"type": "product"})
        
        # Search by content
        results = await memory.search("John")
        assert len(results) == 1
        assert results[0].key == "user:123"
        
        # Search with filters
        results = await memory.search("", filters={"type": "user"})
        assert len(results) == 2
        
        # Search with limit
        results = await memory.search("", limit=1)
        assert len(results) == 1


@pytest.mark.asyncio
async def test_working_memory_delete_and_clear():
    """Test deletion operations."""
    async with WorkingMemory() as memory:
        # Store test data
        await memory.store("keep_1", "value1")
        await memory.store("delete_1", "value2")
        await memory.store("delete_2", "value3")
        
        # Delete single entry
        deleted = await memory.delete("delete_1")
        assert deleted is True
        assert await memory.retrieve("delete_1") is None
        assert await memory.retrieve("keep_1") is not None
        
        # Delete non-existent
        deleted = await memory.delete("missing")
        assert deleted is False
        
        # Clear with pattern
        await memory.store("prefix:1", "value")
        await memory.store("prefix:2", "value")
        cleared = await memory.clear("prefix:")
        assert cleared == 2
        assert await memory.retrieve("prefix:1") is None
        assert await memory.retrieve("keep_1") is not None
        
        # Clear all
        cleared = await memory.clear()
        assert cleared >= 1
        keys = await memory.list_keys()
        assert len(keys) == 0


@pytest.mark.asyncio
async def test_working_memory_list_keys():
    """Test key listing."""
    async with WorkingMemory() as memory:
        # Store test data
        for i in range(5):
            await memory.store(f"test:{i}", f"value_{i}")
        for i in range(3):
            await memory.store(f"other:{i}", f"value_{i}")
            
        # List all keys
        keys = await memory.list_keys()
        assert len(keys) == 8
        
        # List with pattern
        keys = await memory.list_keys("test:")
        assert len(keys) == 5
        assert all(k.startswith("test:") for k in keys)
        
        # List with limit
        keys = await memory.list_keys(limit=3)
        assert len(keys) == 3


@pytest.mark.asyncio 
async def test_working_memory_lru_eviction():
    """Test LRU eviction policy."""
    config = MemoryConfig(backend="memory", max_entries=3)
    
    async with WorkingMemory(config) as memory:
        # Store 3 entries
        await memory.store("a", "value_a")
        await memory.store("b", "value_b") 
        await memory.store("c", "value_c")
        
        # Access 'a' to make it recently used
        await memory.retrieve("a")
        
        # Add new entry - 'b' should be evicted (least recently used)
        await memory.store("d", "value_d")
        
        assert await memory.retrieve("a") is not None  # Recently accessed
        assert await memory.retrieve("b") is None      # Evicted
        assert await memory.retrieve("c") is not None  # Still there
        assert await memory.retrieve("d") is not None  # Newly added 