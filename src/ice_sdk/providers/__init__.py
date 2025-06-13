# ruff: noqa: E402

from __future__ import annotations

"""Provider-specific integrations (LLM, vector DBs, etc.).

For now we only migrate the LLM provider handlers and `LLMService` from the
legacy `ice_tools` namespace.  Code elsewhere in the project should import via

    from ice_sdk.providers import LLMService

or a concrete handler:

    from ice_sdk.providers.llm_providers import OpenAIHandler

Legacy import paths under `ice_tools.llm_providers` are kept as thin shims to
avoid breakage while we migrate gradually.
"""

from importlib import import_module
from types import ModuleType
from typing import Any, cast

__all__: list[str] = [
    "LLMService",
    # Low-level handlers (lazy-loaded on access)
    "OpenAIHandler",
    "AnthropicHandler",
    "GoogleGeminiHandler",
    "DeepSeekHandler",
]


# ---------------------------------------------------------------------------
# Lazy loader helpers --------------------------------------------------------
# ---------------------------------------------------------------------------


class _LazyModuleProxy(ModuleType):
    """Proxy that loads the *real* module upon first attribute access."""

    def __init__(self, target_module: str):
        super().__init__(target_module)
        self._target_module = target_module
        self._real_module: ModuleType | None = None

    def _load(self) -> ModuleType:
        if self._real_module is None:
            self._real_module = import_module(self._target_module)
        return self._real_module

    def __getattr__(self, item: str) -> Any:  # noqa: D401 – passthrough attr access
        return getattr(self._load(), item)


# Expose top-level symbols with lazy import semantics -----------------------
LLMService = cast(Any, _LazyModuleProxy("ice_sdk.providers.llm_service"))

# Handler sub-package --------------------------------------------------------
_llm_pkg = "ice_sdk.providers.llm_providers"
OpenAIHandler = cast(Any, _LazyModuleProxy(f"{_llm_pkg}.openai_handler"))
AnthropicHandler = cast(Any, _LazyModuleProxy(f"{_llm_pkg}.anthropic_handler"))
GoogleGeminiHandler = cast(Any, _LazyModuleProxy(f"{_llm_pkg}.google_gemini_handler"))
DeepSeekHandler = cast(Any, _LazyModuleProxy(f"{_llm_pkg}.deepseek_handler")) 