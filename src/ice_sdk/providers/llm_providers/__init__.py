# ruff: noqa: E402

from __future__ import annotations

"""LLM provider handlers (migrated from `ice_tools.llm_providers`)."""

from importlib import import_module
from typing import Any, cast

__all__: list[str] = [
    "OpenAIHandler",
    "AnthropicHandler",
    "GoogleGeminiHandler",
    "DeepSeekHandler",
]

_prefix = "ice_sdk.providers.llm_providers."

OpenAIHandler = cast(Any, import_module(_prefix + "openai_handler").OpenAIHandler)
AnthropicHandler = cast(Any, import_module(_prefix + "anthropic_handler").AnthropicHandler)
GoogleGeminiHandler = cast(Any, import_module(_prefix + "google_gemini_handler").GoogleGeminiHandler)
DeepSeekHandler = cast(Any, import_module(_prefix + "deepseek_handler").DeepSeekHandler) 