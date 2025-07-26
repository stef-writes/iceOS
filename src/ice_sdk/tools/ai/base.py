"""Base classes for AI-powered tools."""
from typing import Dict, Any, Optional
from ice_sdk.tools.base import ToolBase
from ice_core.models import LLMConfig, ModelProvider


class AITool(ToolBase):
    """Base class for AI-powered tools that use LLM services.
    
    These tools leverage language models for intelligent operations
    like summarization, analysis, and content generation.
    """
    
    category: str = "ai"
    requires_llm: bool = True
    is_deterministic: bool = False  # LLM outputs can vary
    
    # Default LLM configuration (can be overridden)
    default_model: str = "gpt-3.5-turbo"
    default_provider: ModelProvider = ModelProvider.OPENAI
    default_temperature: float = 0.7
    
    def get_category_metadata(self) -> Dict[str, Any]:
        """Return metadata specific to AI tools."""
        return {
            "category": self.category,
            "requires_llm": self.requires_llm,
            "is_deterministic": self.is_deterministic,
            "cost_per_call": self.estimate_cost(),
            "typical_latency_ms": 2000,  # LLM calls are slower
            "model": self.default_model,
            "provider": self.default_provider.value
        }
    
    def estimate_cost(self) -> float:
        """Estimate cost per call based on model and typical usage."""
        # Rough estimates per 1K tokens
        cost_map = {
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.002,
            "claude-2": 0.01,
            "claude-instant": 0.001
        }
        
        base_cost = cost_map.get(self.default_model, 0.002)
        # Assume average 500 tokens per call
        return base_cost * 0.5
    
    def get_llm_config(self, **overrides) -> LLMConfig:
        """Get LLM configuration with optional overrides."""
        return LLMConfig(
            provider=overrides.get("provider", self.default_provider),
            model=overrides.get("model", self.default_model),
            temperature=overrides.get("temperature", self.default_temperature),
            max_tokens=overrides.get("max_tokens", 1000),
            timeout=30
        ) 