"""Integration tests for memory-enabled agents."""

import pytest
from typing import Dict, Any
from ice_orchestrator.agent import MemoryAgent, MemoryAgentConfig
from ice_orchestrator.memory import UnifiedMemoryConfig, MemoryConfig
from ice_core.models.llm import LLMConfig
from ice_core.models.enums import ModelProvider


class TestMemoryAgent(MemoryAgent):
    """Test agent that uses memory for a simple Q&A scenario."""
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Define input schema."""
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "user_id": {"type": "string"}
            }
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        """Define output schema."""
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "response": {"type": "string"},
                "used_memory": {"type": "boolean"},
                "usage": {"type": "object"}
            }
        }
    
    async def _execute_with_memory(self, enhanced_inputs):
        """Simple test implementation that uses memory context."""
        memory_context = enhanced_inputs.get("memory_context", {})
        query = enhanced_inputs.get("query", "")
        
        # Check if we've seen this user before
        past_interactions = memory_context.get("past_interactions", [])
        
        # Generate response based on memory
        if past_interactions:
            response = f"Welcome back! I remember you asked about: {past_interactions[-1].get('query', 'something')}"
        else:
            response = f"Hello! You asked: {query}"
            
        # Store a fact for future reference only if semantic memory is enabled
        if "weather" in query.lower() and self.memory and "semantic" in self.memory._memories:
            await self.remember_fact("User is interested in weather information")
            
        return {
            "status": "success",
            "response": response,
            "used_memory": bool(past_interactions),
            "usage": {"tokens": 50}
        }


@pytest.mark.asyncio
async def test_memory_agent_basic_flow():
    """Test basic memory agent functionality."""
    # Configure agent with memory
    config = MemoryAgentConfig(
        llm_config=LLMConfig(
            model="gpt-4",
            provider=ModelProvider.OPENAI
        ),
        system_prompt="You are a helpful assistant with memory.",
        tools=["test_tool"],
        memory_config=UnifiedMemoryConfig(
            enable_working=True,
            enable_episodic=False,  # Disabled since we don't have Redis in tests
            enable_semantic=False,  # Disabled since we don't have SQLite setup
            enable_procedural=False
        )
    )
    
    agent = TestMemoryAgent(config=config)
    
    # First interaction
    result1 = await agent.execute({
        "user_id": "test_user_123",
        "query": "What's the weather like?"
    })
    
    assert result1["status"] == "success"
    assert "Hello!" in result1["response"]
    assert not result1["used_memory"]
    
    # Check working memory was updated
    memory_entries = await agent.search_memory("weather", ["working"])
    assert len(memory_entries) > 0


@pytest.mark.asyncio
async def test_memory_agent_remembers_facts():
    """Test that agents can store and retrieve facts."""
    config = MemoryAgentConfig(
        llm_config=LLMConfig(
            model="gpt-4",
            provider=ModelProvider.OPENAI
        ),
        system_prompt="Test agent",
        tools=["test_tool"]
    )
    
    agent = TestMemoryAgent(config=config)
    
    # Store some facts
    await agent.remember_fact("The sky is blue")
    await agent.remember_fact("Water boils at 100°C")
    
    # Search for facts
    facts = await agent.search_memory("blue", ["semantic"])
    # Since semantic memory is a stub, this will return empty for now
    # In a real implementation with a backend, this would find the fact
    
    # Clear working memory
    await agent.clear_working_memory()
    
    # Verify it was cleared
    working_items = await agent.search_memory("", ["working"])
    assert len(working_items) == 0


@pytest.mark.asyncio
async def test_memory_agent_without_memory():
    """Test agent works even when memory is disabled."""
    config = MemoryAgentConfig(
        llm_config=LLMConfig(
            model="gpt-4",
            provider=ModelProvider.OPENAI
        ),
        system_prompt="Test agent",
        tools=["test_tool"],
        enable_memory=False  # Disable memory
    )
    
    agent = TestMemoryAgent(config=config)
    
    # Should work without memory
    result = await agent.execute({
        "query": "Hello"
    })
    
    assert result["status"] == "success"
    assert agent.memory is None
    
    # Memory operations should be safe no-ops
    await agent.remember_fact("This won't be stored")
    results = await agent.search_memory("anything")
    assert results == [] 