"""Unified memory interface combining all memory types."""

from typing import Any, Dict, List, Optional
from .base import BaseMemory, MemoryConfig, MemoryEntry
from .working import WorkingMemory
from .episodic import EpisodicMemory
from .semantic import SemanticMemory
from .procedural import ProceduralMemory


class UnifiedMemoryConfig(MemoryConfig):
    """Configuration for unified memory system."""
    
    # Sub-memory configurations
    working_config: Optional[MemoryConfig] = None
    episodic_config: Optional[MemoryConfig] = None
    semantic_config: Optional[MemoryConfig] = None
    procedural_config: Optional[MemoryConfig] = None
    
    # Which memory types to enable
    enable_working: bool = True
    enable_episodic: bool = True
    enable_semantic: bool = True
    enable_procedural: bool = True


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
        
        # Initialize enabled memory types
        if config.enable_working:
            self._memories["working"] = WorkingMemory(
                config.working_config or MemoryConfig(backend="memory")
            )
            
        if config.enable_episodic:
            self._memories["episodic"] = EpisodicMemory(
                config.episodic_config or MemoryConfig(backend="redis")
            )
            
        if config.enable_semantic:
            self._memories["semantic"] = SemanticMemory(
                config.semantic_config or MemoryConfig(backend="sqlite")
            )
            
        if config.enable_procedural:
            self._memories["procedural"] = ProceduralMemory(
                config.procedural_config or MemoryConfig(backend="file")
            )
            
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