from __future__ import annotations

"""Provider/model capability registry.

Defines feature flags and token limits for known models. This enables routing
and policy checks without coupling higher layers to specific vendors.

Rules:
- No external deps; keep in core
- Conservative defaults when a model is unknown
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelCapabilities(BaseModel):
    """Capabilities for a specific provider+model.

    Attributes
    ----------
    provider : str
        Provider key (e.g., "openai", "anthropic").
    model : str
        Model identifier (lowercase).
    supports_tool_calls : bool
        Whether function/tool calling is supported.
    supports_json_mode : bool
        Whether strict JSON-mode outputs are supported.
    supports_vision : bool
        Whether the model can accept/image inputs.
    max_input_tokens : int
        Maximum context length (prompt tokens).
    max_output_tokens : int
        Maximum completion tokens per request.
    """

    provider: str = Field(...)
    model: str = Field(...)
    supports_tool_calls: bool = Field(default=False)
    supports_json_mode: bool = Field(default=False)
    supports_vision: bool = Field(default=False)
    max_input_tokens: int = Field(default=8192)
    max_output_tokens: int = Field(default=4096)


_REGISTRY: Dict[str, Dict[str, ModelCapabilities]] = {
    "openai": {
        "gpt-4o": ModelCapabilities(
            provider="openai",
            model="gpt-4o",
            supports_tool_calls=True,
            supports_json_mode=True,
            supports_vision=True,
            max_input_tokens=128_000,
            max_output_tokens=16_000,
        ),
        "gpt-4o-mini": ModelCapabilities(
            provider="openai",
            model="gpt-4o-mini",
            supports_tool_calls=True,
            supports_json_mode=True,
            supports_vision=True,
            max_input_tokens=128_000,
            max_output_tokens=16_000,
        ),
    },
    "anthropic": {
        "claude-3-5-sonnet": ModelCapabilities(
            provider="anthropic",
            model="claude-3-5-sonnet",
            supports_tool_calls=True,
            supports_json_mode=True,
            supports_vision=False,
            max_input_tokens=200_000,
            max_output_tokens=8_000,
        )
    },
    "google": {
        "gemini-1.5-pro": ModelCapabilities(
            provider="google",
            model="gemini-1.5-pro",
            supports_tool_calls=True,
            supports_json_mode=True,
            supports_vision=True,
            max_input_tokens=1_000_000,
            max_output_tokens=8_000,
        )
    },
    "deepseek": {
        "deepseek-chat": ModelCapabilities(
            provider="deepseek",
            model="deepseek-chat",
            supports_tool_calls=True,
            supports_json_mode=False,
            supports_vision=False,
            max_input_tokens=64_000,
            max_output_tokens=8_000,
        )
    },
}


def get_capabilities(
    provider: str | None, model: str | None
) -> Optional[ModelCapabilities]:
    """Return capabilities for a provider+model or None if unknown.

    Parameters
    ----------
    provider : str | None
        Provider id in lowercase.
    model : str | None
        Model name in lowercase.

    Returns
    -------
    ModelCapabilities | None
        Capability object when known; otherwise None.

    Example
    -------
    >>> caps = get_capabilities("openai", "gpt-4o")
    >>> caps is None or caps.supports_tool_calls
    True
    """

    if not provider or not model:
        return None
    p = provider.lower()
    m = model.lower()
    by_provider = _REGISTRY.get(p)
    if not by_provider:
        return None
    return by_provider.get(m)


__all__ = ["ModelCapabilities", "get_capabilities"]
