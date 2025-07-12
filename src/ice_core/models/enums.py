"""Enumerations shared by core domain models."""

from __future__ import annotations

from enum import Enum

__all__: list[str] = [
    "ModelProvider",
]


class ModelProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    CUSTOM = "custom"
