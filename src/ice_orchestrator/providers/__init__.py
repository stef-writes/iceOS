"""Provider integrations for orchestrator runtime.

This wrapper exposes provider-related runtime helpers while delegating all
LLM-specific functionality to the `ice_core` layer.  By importing from core we
avoid duplicating logic and keep a clean layering boundary (orchestrator may
import core, but not vice-versa).
"""

from ice_core.llm.service import LLMService  # noqa: F401
from ice_core.llm.providers import (
    OpenAIHandler,  # noqa: F401
    AnthropicHandler,  # noqa: F401
    GoogleGeminiHandler,  # noqa: F401
    DeepSeekHandler,  # noqa: F401
)

__all__: list[str] = [
    "LLMService",
    "OpenAIHandler",
    "AnthropicHandler",
    "GoogleGeminiHandler",
    "DeepSeekHandler",
]
