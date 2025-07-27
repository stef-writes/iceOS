"""Base memory protocol and configuration models."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from ice_core.models.enums import ModelProvider

T = TypeVar('T')


class MemoryConfig(BaseModel):
    """Configuration for memory subsystems."""
    
    model_config = ConfigDict(extra="forbid")
    
    # Storage backend configuration
    backend: str = Field(
        default="redis",
        description="Storage backend: redis, sqlite, memory, supabase"
    )
    
    # TTL and retention
    ttl_seconds: Optional[int] = Field(
        default=3600,
        description="Time-to-live for memory entries in seconds"
    )
    max_entries: Optional[int] = Field(
        default=1000,
        description="Maximum number of entries to retain"
    )
    
    # Vector search configuration (optional)
    enable_vector_search: bool = Field(
        default=False,
        description="Enable semantic/vector search capabilities"
    )
    embedding_model: Optional[str] = Field(
        default="text-embedding-3-small",
        description="Model to use for embeddings"
    )
    embedding_provider: Optional[ModelProvider] = Field(
        default=ModelProvider.OPENAI,
        description="Provider for embedding model"
    )
    
    # Connection details
    connection_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Backend-specific connection parameters"
    )


class MemoryEntry(BaseModel):
    """A single memory entry with metadata."""
    
    key: str = Field(..., description="Unique identifier")
    content: Any = Field(..., description="The actual memory content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this memory was created"
    )
    access_count: int = Field(
        default=0,
        description="Number of times accessed"
    )
    importance: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Importance score for retention"
    )


class BaseMemory(ABC):
    """Abstract base class for all memory implementations.
    
    This protocol defines the interface that all memory types must implement.
    It's designed to be async-first and support both simple key-value and
    semantic search operations.
    """
    
    def __init__(self, config: MemoryConfig):
        """Initialize memory with configuration.
        
        Args:
            config: Memory configuration
        """
        self.config = config
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the memory backend (connect to storage, etc)."""
        pass
    
    @abstractmethod
    async def store(
        self, 
        key: str, 
        content: Any, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store a memory entry.
        
        Args:
            key: Unique identifier for the memory
            content: The content to store
            metadata: Optional metadata to attach
        """
        pass
    
    @abstractmethod
    async def retrieve(
        self, 
        key: str
    ) -> Optional[MemoryEntry]:
        """Retrieve a specific memory by key.
        
        Args:
            key: The key to look up
            
        Returns:
            The memory entry if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Search for memories matching a query.
        
        Args:
            query: Search query (text or semantic)
            limit: Maximum results to return
            filters: Optional filters to apply
            
        Returns:
            List of matching memory entries
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a memory entry.
        
        Args:
            key: Key to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear memories matching a pattern.
        
        Args:
            pattern: Optional pattern to match (e.g., "user:*")
            
        Returns:
            Number of entries cleared
        """
        pass
    
    @abstractmethod
    async def list_keys(
        self, 
        pattern: Optional[str] = None,
        limit: int = 100
    ) -> List[str]:
        """List memory keys matching a pattern.
        
        Args:
            pattern: Optional pattern to match
            limit: Maximum keys to return
            
        Returns:
            List of matching keys
        """
        pass
    
    async def __aenter__(self) -> "BaseMemory":
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        # Subclasses can override to close connections
        pass
    
    def validate(self) -> None:
        """Validate memory configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.config.backend:
            raise ValueError("Memory backend must be specified") 