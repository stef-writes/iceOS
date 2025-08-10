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

# ----------------------------------------
# Core providers – required deps (fail loud) --------------------------------
# ----------------------------------------

OpenAIHandler = cast(
    Any, import_module("ice_core.llm.providers.openai_handler").OpenAIHandler
)

# ----------------------------------------
# Optional providers – swallow *ImportError* so missing extras don't break
# the whole application. Clients must check for ``None`` before usage.
# ----------------------------------------


def _safe_import(module_path: str, class_name: str) -> Any | None:  # pragma: no cover
    """Return class from *module_path* or *None* if import fails.

    This helper allows optional LLM providers without forcing all downstream
    users to install their heavyweight dependencies.  We intentionally catch
    *ModuleNotFoundError* at the *provider* boundary so that higher layers
    remain unaffected – in line with the repo's layering rules.
    """

    try:
        module = import_module(module_path)
        return getattr(module, class_name)
    except ModuleNotFoundError:
        # The concrete provider dependency (e.g. ``anthropic``) is missing.
        # Return *None* so that caller can decide whether to surface a
        # validation error or fallback gracefully.
        return None


AnthropicHandler = _safe_import(
    "ice_core.llm.providers.anthropic_handler", "AnthropicHandler"
)
GoogleGeminiHandler = _safe_import(
    "ice_core.llm.providers.google_gemini_handler", "GoogleGeminiHandler"
)
DeepSeekHandler = _safe_import(
    "ice_core.llm.providers.deepseek_handler", "DeepSeekHandler"
)

# Maintain *__all__* dynamically to expose only successfully imported symbols.
__all__ = [
    name
    for name in (
        "OpenAIHandler",
        "AnthropicHandler",
        "GoogleGeminiHandler",
        "DeepSeekHandler",
    )
    if locals().get(name) is not None
]
