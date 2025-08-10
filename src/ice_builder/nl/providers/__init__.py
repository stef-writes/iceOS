"""LLM Provider Registry for Natural Language Blueprint Generation.

This module provides a lightweight registry of LLM providers used during
the blueprint generation process. These are distinct from the runtime
LLM handlers in ice_core.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Dict, List, Optional

from ice_core.models.llm import LLMConfig
from ice_core.protocols.llm import ILLMProvider, llm_provider_registry

__all__: List[str] = ["get_provider", "available_providers", "register_provider"]


# Provider registry - populated on import
_registry: Dict[str, ILLMProvider] = {}

# Auto-discover providers in this directory
for _name in (
    "openai_gpt4o_provider",
    "deepseek_r1_provider",
    "anthropic_claude3_provider",
):
    try:
        mod: ModuleType = import_module(f".{_name}", package=__name__)

        # Get the provider class (not the instance)
        provider_class = None
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, ILLMProvider)
                and attr != ILLMProvider
            ):
                provider_class = attr
                break

        if provider_class:
            # Register with the global registry
            llm_provider_registry.register(provider_class)

            # Create a default instance for backward compatibility
            default_config = LLMConfig()
            default_instance = provider_class.create(default_config)
            _registry[default_instance.get_provider_name()] = default_instance

    except (ImportError, AttributeError):
        # Provider not available - skip silently
        pass


def get_provider(name: str, config: Optional[LLMConfig] = None) -> ILLMProvider:
    """Get a provider by name.

    Args:
        name: Provider name (e.g., "openai", "anthropic", "deepseek")
        config: Optional configuration for the provider

    Returns:
        The requested provider

    Raises:
        KeyError: If provider not found
        ValueError: If configuration is invalid
    """
    if config is None:
        config = LLMConfig()

    try:
        return llm_provider_registry.get_provider(name, config)
    except KeyError:
        available = ", ".join(sorted(llm_provider_registry.list_providers()))
        raise KeyError(f"Provider '{name}' not found. Available: {available}")


def available_providers() -> List[str]:
    """List all available provider names.

    Returns:
        Sorted list of provider names
    """
    return sorted(llm_provider_registry.list_providers())


def register_provider(provider_class: type[ILLMProvider]) -> type[ILLMProvider]:
    """Register a new provider class.

    Args:
        provider_class: Provider class to register

    Returns:
        The registered provider class

    Raises:
        TypeError: If provider doesn't implement ILLMProvider
    """
    return llm_provider_registry.register(provider_class)
