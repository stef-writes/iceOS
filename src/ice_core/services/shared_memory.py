"""Shared Memory Pool Service for iceOS.

Provides system-wide shared memory capabilities that leverage iceOS's 
sophisticated 4-tier memory architecture. Available to ALL node types.

Key Features:
- Pool-based isolation (different workflows/nodes can have separate pools)
- Leverages UnifiedMemory (Working, Episodic, Semantic, Procedural)
- Cross-workflow sharing capabilities
- Built-in TTL and cleanup
- O(1) domain-specific access patterns
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from ice_orchestrator.memory.unified import UnifiedMemory, UnifiedMemoryConfig
from ice_sdk.services.locator import ServiceLocator

logger = logging.getLogger(__name__)


class SharedMemoryPool:
    """System-wide shared memory pool using iceOS memory architecture.
    
    This service provides shared memory capabilities for:
    - SWARM coordination between agents
    - Cross-node state sharing in workflows  
    - Cross-workflow coordination
    - Agent conversation history
    - Cached expensive computations
    - Real-time monitoring state
    
    Example Usage:
        # Get pool for swarm coordination
        pool = await shared_memory.get_pool("investment_swarm")
        await pool.store("current_consensus", {"rating": "buy", "confidence": 0.85})
        
        # Share state between workflow nodes
        pool = await shared_memory.get_pool(f"workflow_{workflow_id}")
        await pool.store("approval_history", approval_data)
        
        # Cross-workflow coordination
        global_pool = await shared_memory.get_pool("global")
        await global_pool.store("active_monitors", monitor_registry)
    """
    
    def __init__(self, pool_name: str, ttl_seconds: int = 3600):
        """Initialize shared memory pool.
        
        Args:
            pool_name: Unique identifier for this memory pool
            ttl_seconds: Default TTL for entries (1 hour default)
        """
        self.pool_name = pool_name
        self.ttl_seconds = ttl_seconds
        self._memory: Optional[UnifiedMemory] = None
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the memory pool with enhanced configuration."""
        if self._initialized:
            return
            
        # Configure memory for shared pool usage
        config = UnifiedMemoryConfig(
            enable_working=True,      # For temporary coordination state
            enable_episodic=True,     # For event/interaction history  
            enable_semantic=True,     # For shared facts/entities
            enable_procedural=False,  # Not needed for most shared use cases
            working_config=self._get_working_config(),
            episodic_config=self._get_episodic_config(),
            semantic_config=self._get_semantic_config()
        )
        
        self._memory = UnifiedMemory(config)
        await self._memory.initialize()
        self._initialized = True
        
        logger.info(f"Initialized shared memory pool: {self.pool_name}")
    
    def _get_working_config(self):
        """Configure working memory for shared pool."""
        from ice_orchestrator.memory.base import MemoryConfig
        return MemoryConfig(
            backend="memory",
            ttl_seconds=self.ttl_seconds,
            max_entries=10000  # Large limit for shared pools
        )
    
    def _get_episodic_config(self):
        """Configure episodic memory for interaction history."""
        from ice_orchestrator.memory.base import MemoryConfig
        return MemoryConfig(
            backend="redis",
            ttl_seconds=self.ttl_seconds * 24,  # Keep history longer
            max_entries=50000
        )
    
    def _get_semantic_config(self):
        """Configure semantic memory for shared facts."""
        from ice_orchestrator.memory.base import MemoryConfig
        return MemoryConfig(
            backend="sqlite",
            ttl_seconds=self.ttl_seconds * 7,  # Keep facts even longer
            max_entries=100000
        )
    
    async def store(
        self, 
        key: str, 
        value: Any, 
        memory_type: str = "working",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store value in shared memory.
        
        Args:
            key: Storage key (will be prefixed with pool name)
            value: Value to store
            memory_type: Type of memory ("working", "episodic", "semantic")
            metadata: Optional metadata for the entry
        """
        if not self._initialized:
            await self.initialize()
            
        # Prefix key with pool name for isolation
        pool_key = f"pool:{self.pool_name}:{key}"
        
        # Add pool metadata
        if metadata is None:
            metadata = {}
        metadata.update({
            "pool_name": self.pool_name,
            "stored_at": datetime.utcnow().isoformat(),
            "memory_type": memory_type
        })
        
        await self._memory.store(pool_key, value, metadata, memory_type)
        logger.debug(f"Stored {key} in pool {self.pool_name} ({memory_type})")
    
    async def retrieve(
        self, 
        key: str, 
        memory_type: str = "working"
    ) -> Optional[Any]:
        """Retrieve value from shared memory.
        
        Args:
            key: Storage key
            memory_type: Type of memory to search
            
        Returns:
            Retrieved value or None if not found
        """
        if not self._initialized:
            await self.initialize()
            
        pool_key = f"pool:{self.pool_name}:{key}"
        entry = await self._memory.retrieve(pool_key, memory_type)
        
        if entry:
            logger.debug(f"Retrieved {key} from pool {self.pool_name}")
            return entry.content
        return None
    
    async def list_keys(self, memory_type: str = "working") -> List[str]:
        """List all keys in this pool for given memory type.
        
        Args:
            memory_type: Type of memory to list
            
        Returns:
            List of keys (without pool prefix)
        """
        if not self._initialized:
            await self.initialize()
            
        # Get memory instance for type
        if memory_type == "working" and self._memory.working:
            all_keys = await self._memory.working.list_keys()
        elif memory_type == "episodic" and self._memory.episodic:
            all_keys = await self._memory.episodic.list_keys()  
        elif memory_type == "semantic" and self._memory.semantic:
            all_keys = await self._memory.semantic.list_keys()
        else:
            return []
        
        # Filter for this pool and remove prefix
        pool_prefix = f"pool:{self.pool_name}:"
        pool_keys = []
        for key in all_keys:
            if key.startswith(pool_prefix):
                pool_keys.append(key[len(pool_prefix):])
        
        return pool_keys
    
    async def delete(self, key: str, memory_type: str = "working") -> bool:
        """Delete value from shared memory.
        
        Args:
            key: Storage key
            memory_type: Type of memory
            
        Returns:
            True if deleted, False if not found
        """
        if not self._initialized:
            await self.initialize()
            
        pool_key = f"pool:{self.pool_name}:{key}"
        success = await self._memory.delete(pool_key, memory_type)
        
        if success:
            logger.debug(f"Deleted {key} from pool {self.pool_name}")
        
        return success
    
    async def clear(self, memory_type: Optional[str] = None) -> None:
        """Clear all entries in this pool.
        
        Args:
            memory_type: Specific memory type to clear, or None for all
        """
        if not self._initialized:
            await self.initialize()
            
        memory_types = [memory_type] if memory_type else ["working", "episodic", "semantic"]
        
        for mem_type in memory_types:
            keys = await self.list_keys(mem_type)
            for key in keys:
                await self.delete(key, mem_type)
        
        logger.info(f"Cleared pool {self.pool_name} ({memory_types})")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics for this memory pool."""
        if not self._initialized:
            await self.initialize()
            
        stats = {
            "pool_name": self.pool_name,
            "initialized": self._initialized,
            "working_keys": len(await self.list_keys("working")),
            "episodic_keys": len(await self.list_keys("episodic")),
            "semantic_keys": len(await self.list_keys("semantic")),
            "total_keys": 0
        }
        
        stats["total_keys"] = (
            stats["working_keys"] + 
            stats["episodic_keys"] + 
            stats["semantic_keys"]
        )
        
        return stats


class SharedMemoryService:
    """Service for managing shared memory pools across iceOS.
    
    This service provides:
    - Pool creation and management
    - Pool isolation and cleanup
    - Cross-workflow coordination
    - Performance monitoring
    """
    
    def __init__(self):
        """Initialize the shared memory service."""
        self._pools: Dict[str, SharedMemoryPool] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the service and start cleanup task."""
        # Start background cleanup
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("SharedMemoryService initialized")
    
    async def get_pool(
        self, 
        pool_name: str, 
        ttl_seconds: int = 3600,
        auto_create: bool = True
    ) -> SharedMemoryPool:
        """Get or create a shared memory pool.
        
        Args:
            pool_name: Unique pool identifier
            ttl_seconds: Default TTL for entries in this pool
            auto_create: Whether to create pool if it doesn't exist
            
        Returns:
            SharedMemoryPool instance
            
        Raises:
            ValueError: If pool doesn't exist and auto_create is False
        """
        if pool_name not in self._pools:
            if not auto_create:
                raise ValueError(f"Pool '{pool_name}' does not exist")
            
            pool = SharedMemoryPool(pool_name, ttl_seconds)
            await pool.initialize()
            self._pools[pool_name] = pool
            
            logger.info(f"Created shared memory pool: {pool_name}")
        
        return self._pools[pool_name]
    
    async def delete_pool(self, pool_name: str) -> bool:
        """Delete a shared memory pool and all its data.
        
        Args:
            pool_name: Pool to delete
            
        Returns:
            True if deleted, False if not found
        """
        if pool_name in self._pools:
            pool = self._pools[pool_name]
            await pool.clear()  # Clear all data
            del self._pools[pool_name]
            logger.info(f"Deleted shared memory pool: {pool_name}")
            return True
        return False
    
    async def list_pools(self) -> List[str]:
        """List all active memory pools."""
        return list(self._pools.keys())
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get statistics for all memory pools."""
        stats = {
            "total_pools": len(self._pools),
            "pools": {}
        }
        
        for pool_name, pool in self._pools.items():
            pool_stats = await pool.get_stats()
            stats["pools"][pool_name] = pool_stats
        
        return stats
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup of unused pools."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                # Could add logic to cleanup unused pools here
                pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the service and cleanup resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clear all pools
        for pool_name in list(self._pools.keys()):
            await self.delete_pool(pool_name)
        
        logger.info("SharedMemoryService shutdown complete")


# Singleton instance for dependency injection
_shared_memory_service: Optional[SharedMemoryService] = None


async def get_shared_memory_service() -> SharedMemoryService:
    """Get the global shared memory service instance."""
    global _shared_memory_service
    
    if _shared_memory_service is None:
        _shared_memory_service = SharedMemoryService()
        await _shared_memory_service.initialize()
        
        # Register with ServiceLocator for dependency injection
        try:
            ServiceLocator.register("shared_memory", _shared_memory_service)
        except Exception as e:
            logger.warning(f"Could not register with ServiceLocator: {e}")
    
    return _shared_memory_service 