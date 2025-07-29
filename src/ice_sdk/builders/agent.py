"""Agent builder utilities for developers."""

from typing import Dict, List, Optional, Any
from ice_core.models import ModelProvider


class AgentBuilder:
    """Builder for creating agent configurations for workflows."""
    
    def __init__(self, name: str = "agent"):
        self.config = {
            "type": "agent",
            "id": name,
            "config": {
                "tools": [],
                "max_retries": 3,
            }
        }
        
    def with_llm(self, model: str = "gpt-4", provider: ModelProvider = ModelProvider.OPENAI) -> "AgentBuilder":
        """Set the LLM configuration for the agent."""
        self.config["config"]["llm_config"] = {
            "provider": provider.value,
            "model": model,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        return self
        
    def with_system_prompt(self, prompt: str) -> "AgentBuilder":
        """Set the system prompt for the agent."""
        self.config["config"]["system_prompt"] = prompt
        return self
        
    def with_tools(self, tools: List[str]) -> "AgentBuilder":
        """Set the allowed tools for the agent."""
        self.config["config"]["tools"] = tools
        return self
        
    def with_memory(self, memory_config: Optional[Dict[str, Any]] = None) -> "AgentBuilder":
        """Enable memory for the agent."""
        self.config["config"]["enable_memory"] = True
        if memory_config:
            self.config["config"]["memory_config"] = memory_config
        return self
        
    def with_max_retries(self, max_retries: int) -> "AgentBuilder":
        """Set the maximum number of retries for the agent."""
        self.config["config"]["max_retries"] = max_retries
        return self
        
    def build(self) -> Dict[str, Any]:
        """Build the agent configuration."""
        # Validate required fields
        if "llm_config" not in self.config["config"]:
            raise ValueError("Agent requires LLM configuration. Call with_llm() first.")
        if "system_prompt" not in self.config["config"]:
            raise ValueError("Agent requires system prompt. Call with_system_prompt() first.")
            
        return self.config
        

def create_agent(name: str = "agent") -> AgentBuilder:
    """Create a new agent builder."""
    return AgentBuilder(name) 