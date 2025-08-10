"""LLM Provider Protocol Definition.

This module defines the protocol that all LLM providers must implement
for consistent behavior across the iceOS ecosystem.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Type

from ice_core.models.llm import LLMConfig


class ILLMProvider(ABC):
    """Abstract base class for LLM providers with enforced protocol compliance.

    This protocol ensures all providers implement the required interface
    for consistent behavior across the iceOS ecosystem.
    """

    @classmethod
    @abstractmethod
    def create(cls, config: LLMConfig) -> ILLMProvider:
        """Factory method required for all providers.

        Args:
            config: LLM configuration with provider-specific settings

        Returns:
            Configured provider instance
        """
        ...

    @abstractmethod
    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:
        """Core streaming interface for real-time text generation.

        Args:
            prompt: Input prompt for text generation

        Yields:
            Generated text chunks
        """
        ...

    @abstractmethod
    async def complete(self, prompt: str) -> str:
        """Generate a complete response for the given prompt.

        Args:
            prompt: Input prompt for text generation

        Returns:
            Complete generated text
        """
        ...

    @abstractmethod
    def get_cost_estimate(self, prompt: str) -> float:
        """Estimate the cost for processing the given prompt.

        Args:
            prompt: Input prompt to estimate cost for

        Returns:
            Estimated cost in USD
        """
        ...

    @classmethod
    @abstractmethod
    def supported_models(cls) -> List[str]:
        """Return list of supported model identifiers.

        Returns:
            List of model names supported by this provider
        """
        ...

    @classmethod
    @abstractmethod
    def get_provider_name(cls) -> str:
        """Return the provider's unique identifier.

        Returns:
            Provider name (e.g., 'anthropic', 'openai')
        """
        ...

    @abstractmethod
    def validate_config(self, config: LLMConfig) -> bool:
        """Validate provider-specific configuration.

        Args:
            config: LLM configuration to validate

        Returns:
            True if configuration is valid for this provider

        Raises:
            ValueError: If configuration is invalid
        """
        ...

    @property
    @abstractmethod
    def model_identifier(self) -> str:
        """Return the current model identifier.

        Returns:
            Current model name/version
        """
        ...


class LLMProviderRegistry:
    """Registry for LLM providers with protocol enforcement."""

    def __init__(self) -> None:
        self._providers: Dict[str, Type[ILLMProvider]] = {}

    def register(self, provider_class: Type[ILLMProvider]) -> Type[ILLMProvider]:
        """Register a provider class with protocol validation.

        Args:
            provider_class: Provider class to register

        Returns:
            The registered provider class

        Raises:
            TypeError: If provider doesn't implement required protocol
        """
        if not issubclass(provider_class, ILLMProvider):
            raise TypeError(f"{provider_class.__name__} doesn't implement ILLMProvider")

        provider_name = provider_class.get_provider_name()
        self._providers[provider_name] = provider_class
        return provider_class

    def get_provider(self, provider_name: str, config: LLMConfig) -> ILLMProvider:
        """Get a configured provider instance.

        Args:
            provider_name: Name of the provider to get
            config: Configuration for the provider

        Returns:
            Configured provider instance

        Raises:
            KeyError: If provider is not registered
            ValueError: If configuration is invalid
        """
        if provider_name not in self._providers:
            raise KeyError(f"Provider '{provider_name}' not registered")

        provider_class = self._providers[provider_name]
        provider = provider_class.create(config)

        # Validate configuration
        if not provider.validate_config(config):
            raise ValueError(f"Invalid configuration for provider '{provider_name}'")

        return provider

    def list_providers(self) -> List[str]:
        """List all registered provider names.

        Returns:
            List of registered provider names
        """
        return list(self._providers.keys())

    def get_provider_class(self, provider_name: str) -> Type[ILLMProvider]:
        """Get the provider class by name.

        Args:
            provider_name: Name of the provider

        Returns:
            Provider class

        Raises:
            KeyError: If provider is not registered
        """
        if provider_name not in self._providers:
            raise KeyError(f"Provider '{provider_name}' not registered")

        return self._providers[provider_name]


# Global registry instance
llm_provider_registry = LLMProviderRegistry()
