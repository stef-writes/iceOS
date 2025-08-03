"""Anthropic Claude-3 Haiku provider for natural language blueprint generation.

This provider wraps the ice_core LLM service to call Anthropic's Claude-3 Haiku model,
optimized for code generation and implementation details.
"""
from __future__ import annotations

from typing import AsyncGenerator

from ice_core.models.llm import LLMConfig
from ice_core.models.enums import ModelProvider
from ice_core.protocols.llm import ILLMProvider


from ice_core.protocols import enforce_protocol

@enforce_protocol(ILLMProvider)
class AnthropicClaude3Provider(ILLMProvider):
    """Provider for Claude-3 Haiku model optimized for code generation."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._model = "claude-3-haiku-20240307"
    
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
        """Stream response from Claude-3 Haiku.
        
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
        """Return a stubbed completion (NL generator disabled during hardening).
        
        Args:
            prompt: The input prompt to complete.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Maximum tokens to generate (defaults to model config).
            
        Returns:
            Generated text completion.
            
        Raises:
            RuntimeError: If the LLM service returns an error.
        """
        # During hardening the NL generator is disabled; this stub avoids
        # external side-effects while maintaining protocol compliance.
        return ""
    
    def get_cost_estimate(self, prompt: str) -> float:
        """Estimate cost for processing the prompt.
        
        Args:
            prompt: Input prompt to estimate cost for
            
        Returns:
            Estimated cost in USD
        """
        # Claude-3 Haiku pricing: $0.25 per 1M input tokens, $1.25 per 1M output tokens
        # Rough estimate: assume 1:1 input/output ratio
        token_count = len(prompt.split()) * 1.3  # Rough token estimation
        return (token_count / 1_000_000) * 0.25
    
    @classmethod
    def supported_models(cls) -> list[str]:
        """Return list of supported model identifiers.
        
        Returns:
            List of supported Claude models
        """
        return [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
        ]
    
    @classmethod
    def get_provider_name(cls) -> str:
        """Return the provider's unique identifier.
        
        Returns:
            Provider name
        """
        return "anthropic"
    
    def validate_config(self, config: LLMConfig) -> bool:
        """Validate provider-specific configuration.
        
        Args:
            config: LLM configuration to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if config.provider != ModelProvider.ANTHROPIC:
            raise ValueError("Anthropic provider requires ANTHROPIC provider type")
        
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


