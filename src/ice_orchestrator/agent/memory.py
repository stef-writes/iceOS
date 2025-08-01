"""Memory-enabled agent base class."""

from typing import Any, Dict, List, Optional

from pydantic import Field, PrivateAttr

from ice_core.memory import UnifiedMemory, UnifiedMemoryConfig
from ice_core.models.node_models import AgentNodeConfig

from .base import AgentNode


class MemoryAgentConfig(AgentNodeConfig):
    """Configuration for memory-enabled agents."""
    
    memory_config: Optional[UnifiedMemoryConfig] = Field(
        default=None,
        description="Memory subsystem configuration"
    )
    enable_memory: bool = Field(
        default=True,
        description="Whether to enable memory for this agent"
    )


class MemoryAgent(AgentNode):
    """Base class for agents with integrated memory capabilities.
    
    This extends AgentNode to provide:
    - Unified memory interface
    - Automatic context loading from memory
    - Memory persistence between interactions
    - Built-in memory search and retrieval
    """
    
    config: MemoryAgentConfig
    memory: Optional[UnifiedMemory] = Field(default=None, description="Memory instance")
    _memory_initialized: bool = PrivateAttr(default=False)
    
    def __init__(self, config: MemoryAgentConfig, memory: Optional[UnifiedMemory] = None):
        """Initialize memory agent with dependency injection.
        
        Args:
            config: Agent configuration
            memory: Memory instance (injected dependency)
        """
        super().__init__(config=config)
        if memory is not None:
            self.memory = memory
        elif config.enable_memory:
            memory_config = config.memory_config or UnifiedMemoryConfig()
            self.memory = UnifiedMemory(memory_config)
            
    async def _execute_agent_cycle(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent cycle with memory integration."""
        # Initialize memory if needed
        if self.memory and not self._memory_initialized:
            await self.memory.initialize()
            self._memory_initialized = True
            
        # Load relevant context from memory
        context = await self._load_memory_context(inputs)
        
        # Merge with inputs
        enhanced_inputs = {
            **inputs,
            "memory_context": context
        }
        
        # Execute main agent logic (to be implemented by subclasses)
        result = await self._execute_with_memory(enhanced_inputs)
        
        # Store important results in memory
        await self._update_memory(inputs, result)
        
        return result
        
    async def _load_memory_context(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load relevant context from memory.
        
        Args:
            inputs: Current inputs to help determine what to load
            
        Returns:
            Context dictionary with relevant memories
        """
        if not self.memory:
            return {}
            
        context: Dict[str, Any] = {}
        
        # Get working memory context
        if "working" in self.memory._memories:
            context["working"] = await self.memory.get_working_context()
        
        # Search for relevant past episodes if there's a user_id
        user_id = inputs.get("user_id")
        if user_id and "episodic" in self.memory._memories:
            episodes = await self.memory.search(
                f"user:{user_id}",
                memory_types=["episodic"],
                limit=5
            )
            context["past_interactions"] = [e.content for e in episodes]
            
        # Search for relevant facts based on query
        query = inputs.get("query", inputs.get("message", ""))
        if query and "semantic" in self.memory._memories:
            facts = await self.memory.search(
                query,
                memory_types=["semantic"],
                limit=10
            )
            context["relevant_facts"] = [f.content for f in facts]
            
        return context
        
    async def _update_memory(
        self, 
        inputs: Dict[str, Any], 
        result: Dict[str, Any]
    ) -> None:
        """Update memory with interaction results.
        
        Args:
            inputs: Original inputs
            result: Execution results
        """
        if not self.memory:
            return
            
        # Store in working memory for immediate use
        if "working" in self.memory._memories:
            await self.memory.store(
                "work:last_interaction",
                {
                    "inputs": inputs,
                    "result": result,
                    "timestamp": str(datetime.now())
                }
            )
        
        # Store episode if there's a user interaction
        user_id = inputs.get("user_id")
        if user_id and result.get("response") and "episodic" in self.memory._memories:
            await self.memory.remember_episode({
                "user_id": user_id,
                "query": inputs.get("query", ""),
                "response": result.get("response"),
                "timestamp": str(datetime.now()),
                "metadata": {
                    "success": result.get("success", True),
                    "tokens_used": result.get("usage", {}).get("tokens", 0)
                }
            })
            
    async def _execute_with_memory(
        self, 
        enhanced_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute main agent logic with memory-enhanced inputs.
        
        Subclasses should override this method.
        
        Args:
            enhanced_inputs: Inputs enhanced with memory context
            
        Returns:
            Execution results
        """
        # Default implementation - subclasses should override
        return await super()._execute_agent_cycle(enhanced_inputs)
        
    async def remember_fact(self, fact: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a fact in semantic memory.
        
        Args:
            fact: The fact to remember
            metadata: Optional metadata about the fact
        """
        if self.memory:
            await self.memory.remember_fact(fact, metadata)
            
    async def search_memory(
        self, 
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Any]:
        """Search across memory types.
        
        Args:
            query: Search query
            memory_types: Types to search (all if None)
            limit: Maximum results
            
        Returns:
            List of memory entries
        """
        if not self.memory:
            return []
            
        results = await self.memory.search(query, memory_types, limit)
        return [r.content for r in results]
        
    async def clear_working_memory(self) -> None:
        """Clear working memory (useful between tasks)."""
        if self.memory and "working" in self.memory._memories:
            await self.memory._memories["working"].clear()


# Import at the end to avoid circular imports
from datetime import datetime
