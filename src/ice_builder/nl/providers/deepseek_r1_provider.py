"""DeepSeek R1 provider for natural language blueprint generation.

This provider wraps the ice_core LLM service to call DeepSeek's R1 model,
optimized for planning, reasoning, and structured output generation.
"""
from __future__ import annotations

from typing import AsyncGenerator

from ice_core.models.llm import LLMConfig
from ice_core.models.enums import ModelProvider
from ice_core.protocols.llm import ILLMProvider


from ice_core.protocols import enforce_protocol

@enforce_protocol(ILLMProvider)
class DeepSeekR1Provider(ILLMProvider):
    """Provider for DeepSeek R1 model optimized for planning and reasoning."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._model = "deepseek-r1"
    
    @classmethod
    def create(cls, config: LLMConfig) -> ILLMProvider:
        """Create a new provider instance with the given configuration.
        
        Args:
            config: LLM configuration
            
        Returns:
            Configured provider instance
        """
        return cls(config)
    
    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:  # type: ignore[override]
        """Stream response from DeepSeek R1.
        
        Args:
            prompt: Input prompt for text generation
            
        Yields:
            Generated text chunks
        """
        # For now, we'll use the complete method and yield the result
        # In a real implementation, this would use streaming API
        result = await self.complete(prompt)
        yield result
    
    async def complete(self, prompt: str) -> str:
        """Generate completion using DeepSeek R1 via ice_core's LLM service.
        
        Args:
            prompt: The input prompt to complete.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Maximum tokens to generate (defaults to model config).
            
        Returns:
            Generated text completion.
            
        Raises:
            RuntimeError: If the LLM service returns an error.
        """
        # Stub implementation during protocol hardening
        return ""
    
    def get_cost_estimate(self, prompt: str) -> float:
        """Estimate cost for processing the prompt.
        
        Args:
            prompt: Input prompt to estimate cost for
            
        Returns:
            Estimated cost in USD
        """
        # DeepSeek R1 pricing: approximately $0.002 per 1K tokens
        # Rough estimate: assume 1:1 input/output ratio
        token_count = len(prompt.split()) * 1.3  # Rough token estimation
        return (token_count / 1000) * 0.002
    
    @classmethod
    def supported_models(cls) -> list[str]:
        """Return list of supported model identifiers.
        
        Returns:
            List of supported DeepSeek models
        """
        return [
            "deepseek-r1",
            "deepseek-coder",
            "deepseek-chat",
        ]
    
    @classmethod
    def get_provider_name(cls) -> str:
        """Return the provider's unique identifier.
        
        Returns:
            Provider name
        """
        return "deepseek"
    
    def validate_config(self, config: LLMConfig) -> bool:
        """Validate provider-specific configuration.
        
        Args:
            config: LLM configuration to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if config.provider != ModelProvider.DEEPSEEK:
            raise ValueError("DeepSeek provider requires DEEPSEEK provider type")
        
        if config.temperature is not None and not (0.0 <= config.temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        
        if config.max_tokens is not None and config.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        
        if config.top_p is not None and not (0.0 <= config.top_p <= 1.0):
            raise ValueError("top_p must be between 0.0 and 1.0")
        
        return True
    
    @property
    def model_identifier(self) -> str:
        """Return the current model identifier.
        
        Returns:
            Current model name/version
        """
        return self._model


