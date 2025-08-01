"""Unified memory interface combining all memory types."""

from typing import Any, Dict, List, Optional, Union
from .base import BaseMemory, MemoryConfig, MemoryEntry
from .working import WorkingMemory
from .episodic import EpisodicMemory
from .semantic import SemanticMemory
from .procedural import ProceduralMemory


class UnifiedMemoryConfig(MemoryConfig):
    """Simplified configuration for unified memory system.
    
    This provides sensible defaults while allowing customization when needed.
    """
    
    # Simplified configuration with smart defaults
    backend: str = "redis"
    enable_vector_search: bool = True
    
    # Memory type enablement (all enabled by default)
    enable_working: bool = True
    enable_episodic: bool = True
    enable_semantic: bool = True
    enable_procedural: bool = True
    
    # Domain-specific configuration
    domains: List[str] = ["general", "marketplace", "pricing", "inventory"]
    
    # Advanced configuration (optional)
    working_config: Optional[MemoryConfig] = None
    episodic_config: Optional[MemoryConfig] = None
    semantic_config: Optional[MemoryConfig] = None
    procedural_config: Optional[MemoryConfig] = None


class UnifiedMemory:
    """Unified interface to all memory subsystems.
    
    This provides a single interface for agents to access all memory types.
    It routes operations to the appropriate memory backend based on key patterns
    or explicit memory type specification.
    
    Key patterns:
    - work:* -> Working memory
    - episode:* -> Episodic memory  
    - fact:* -> Semantic memory
    - procedure:* -> Procedural memory
    
    Enhanced API provides direct access:
    - memory.working.store(key, value)
    - memory.episodic.search(query)
    - memory.semantic.retrieve(key)
    - memory.procedural.search(query)
    """
    
    def __init__(self, config: Optional[UnifiedMemoryConfig] = None):
        """Initialize unified memory system.
        
        Args:
            config: Configuration for all memory subsystems
        """
        if config is None:
            config = UnifiedMemoryConfig()
            
        self.config = config
        self._memories: Dict[str, BaseMemory] = {}
        
        # Initialize enabled memory types with smart defaults
        if config.enable_working:
            working_config = config.working_config or MemoryConfig(
                backend="memory",
                enable_vector_search=config.enable_vector_search
            )
            self._memories["working"] = WorkingMemory(working_config)
            
        if config.enable_episodic:
            episodic_config = config.episodic_config or MemoryConfig(
                backend=config.backend,
                enable_vector_search=config.enable_vector_search
            )
            self._memories["episodic"] = EpisodicMemory(episodic_config)
            
        if config.enable_semantic:
            semantic_config = config.semantic_config or MemoryConfig(
                backend=config.backend,
                enable_vector_search=config.enable_vector_search
            )
            self._memories["semantic"] = SemanticMemory(semantic_config)
            
        if config.enable_procedural:
            procedural_config = config.procedural_config or MemoryConfig(
                backend=config.backend,
                enable_vector_search=config.enable_vector_search
            )
            self._memories["procedural"] = ProceduralMemory(procedural_config)
    
    # Enhanced API: Direct access to memory subsystems
    @property
    def working(self) -> Optional[WorkingMemory]:
        """Access working memory directly."""
        memory = self._memories.get("working")
        return memory if isinstance(memory, WorkingMemory) else None
    
    @property 
    def episodic(self) -> Optional[EpisodicMemory]:
        """Access episodic memory directly."""
        memory = self._memories.get("episodic")
        return memory if isinstance(memory, EpisodicMemory) else None
    
    @property
    def semantic(self) -> Optional[SemanticMemory]:
        """Access semantic memory directly."""
        memory = self._memories.get("semantic")
        return memory if isinstance(memory, SemanticMemory) else None
    
    @property
    def procedural(self) -> Optional[ProceduralMemory]:
        """Access procedural memory directly."""
        memory = self._memories.get("procedural")
        return memory if isinstance(memory, ProceduralMemory) else None
            
    async def initialize(self) -> None:
        """Initialize all memory subsystems."""
        for memory in self._memories.values():
            await memory.initialize()
            
    def _get_memory_type(self, key: str) -> str:
        """Determine memory type from key pattern."""
        if key.startswith("work:"):
            return "working"
        elif key.startswith("episode:"):
            return "episodic"
        elif key.startswith("fact:"):
            return "semantic"
        elif key.startswith("procedure:"):
            return "procedural"
        else:
            # Default to working memory
            return "working"
            
    async def store(
        self,
        key: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
        memory_type: Optional[str] = None
    ) -> None:
        """Store content in appropriate memory.
        
        Args:
            key: Storage key
            content: Content to store
            metadata: Optional metadata
            memory_type: Explicit memory type override
        """
        if memory_type is None:
            memory_type = self._get_memory_type(key)
            
        if memory_type not in self._memories:
            raise ValueError(f"Memory type '{memory_type}' not enabled")
            
        await self._memories[memory_type].store(key, content, metadata)
        
    async def retrieve(
        self,
        key: str,
        memory_type: Optional[str] = None
    ) -> Optional[MemoryEntry]:
        """Retrieve from appropriate memory.
        
        Args:
            key: Key to retrieve
            memory_type: Explicit memory type override
            
        Returns:
            Memory entry if found
        """
        if memory_type is None:
            memory_type = self._get_memory_type(key)
            
        if memory_type not in self._memories:
            return None
            
        return await self._memories[memory_type].retrieve(key)
        
    async def search(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Search across specified memory types.
        
        Args:
            query: Search query
            memory_types: Types to search (all if None)
            limit: Max results per type
            filters: Optional filters
            
        Returns:
            Combined results from all searched memories
        """
        if memory_types is None:
            memory_types = list(self._memories.keys())
            
        results = []
        for mem_type in memory_types:
            if mem_type in self._memories:
                type_results = await self._memories[mem_type].search(
                    query, limit, filters
                )
                results.extend(type_results)
                
        return results[:limit]  # Apply overall limit
        
    async def clear_all(self) -> Dict[str, int]:
        """Clear all memories.
        
        Returns:
            Count of cleared entries per memory type
        """
        counts = {}
        for mem_type, memory in self._memories.items():
            counts[mem_type] = await memory.clear()
        return counts
        
    # Convenience methods for specific memory types
    
    async def remember_fact(self, fact: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a fact in semantic memory."""
        key = f"fact:{hash(fact)}"
        await self.store(key, fact, metadata, "semantic")
        
    async def remember_episode(self, episode: Dict[str, Any]) -> None:
        """Store an episode in episodic memory."""
        key = f"episode:{episode.get('timestamp', 'unknown')}"
        await self.store(key, episode, episode.get("metadata"), "episodic")
        
    async def remember_procedure(self, name: str, steps: List[Any]) -> None:
        """Store a procedure in procedural memory."""
        key = f"procedure:{name}"
        await self.store(key, {"name": name, "steps": steps}, None, "procedural")
        
    async def get_working_context(self) -> Dict[str, Any]:
        """Get all working memory as context dict."""
        if "working" not in self._memories:
            return {}
            
        context = {}
        keys = await self._memories["working"].list_keys()
        for key in keys:
            entry = await self._memories["working"].retrieve(key)
            if entry:
                context[key] = entry.content
        return context
        
    async def __aenter__(self) -> "UnifiedMemory":
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        for memory in self._memories.values():
            await memory.__aexit__(exc_type, exc_val, exc_tb)
    
    # Analytics and monitoring methods
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all memory types.
        
        Returns:
            Dictionary with usage statistics per memory type
        """
        stats = {}
        for mem_type, memory in self._memories.items():
            try:
                keys = await memory.list_keys()
                stats[mem_type] = {
                    "entry_count": len(keys),
                    "memory_type": type(memory).__name__,
                    "backend": memory.config.backend
                }
            except Exception as e:
                stats[mem_type] = {"error": str(e)}
        return stats
    
    async def get_domain_analytics(self) -> Dict[str, Any]:
        """Get analytics for domain-specific memory usage.
        
        Returns:
            Dictionary with domain analytics
        """
        analytics = {
            "domains": self.config.domains,
            "domain_usage": {}
        }
        
        for domain in self.config.domains:
            domain_stats: Dict[str, Union[int, Dict[str, str]]] = {}
            for mem_type, memory in self._memories.items():
                try:
                    # Search for domain-specific entries
                    domain_entries = await memory.search(domain, limit=100)
                    domain_stats[mem_type] = len(domain_entries)
                except Exception as e:
                    domain_stats[mem_type] = {"error": str(e)}
            analytics["domain_usage"][domain] = domain_stats
            
        return analytics
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for memory operations.
        
        Returns:
            Dictionary with performance metrics
        """
        import time
        
        metrics = {}
        for mem_type, memory in self._memories.items():
            try:
                # Test write performance
                start = time.time()
                test_key = f"perf_test_{mem_type}_{int(start)}"
                await memory.store(test_key, "test_data")
                write_time = time.time() - start
                
                # Test read performance
                start = time.time()
                await memory.retrieve(test_key)
                read_time = time.time() - start
                
                # Test search performance
                start = time.time()
                await memory.search("test", limit=5)
                search_time = time.time() - start
                
                # Cleanup
                await memory.delete(test_key)
                
                metrics[mem_type] = {
                    "write_time_ms": round(write_time * 1000, 2),
                    "read_time_ms": round(read_time * 1000, 2),
                    "search_time_ms": round(search_time * 1000, 2),
                    "backend": memory.config.backend
                }
            except Exception as e:
                metrics[mem_type] = {"error": str(e)}
                
        return metrics 