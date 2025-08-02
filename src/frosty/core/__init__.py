"""Frosty Core – planner, validator, provider registry."""

from importlib import import_module
from types import ModuleType
from typing import Dict, List

from .providers.base import LLMProvider  # noqa: F401

_registry: Dict[str, LLMProvider] = {}

for _name in ("o3",):
    mod: ModuleType = import_module(f"frosty.core.providers.{_name}")
    provider: LLMProvider = getattr(mod, "PROVIDER")  # type: ignore[assignment]
    _registry[provider.name] = provider


def get_provider(name: str) -> LLMProvider:  # noqa: D401
    return _registry[name]


def available_providers() -> List[str]:  # noqa: D401
    return sorted(_registry.keys())

__all__ = ["LLMProvider", "get_provider", "available_providers"]