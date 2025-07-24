from __future__ import annotations

"""LLM model registry.

This lightweight helper lists *allowed* foundation models with metadata so
higher-level layers (CLI, SDK, orchestrator) can present consistent choices and
validate configurations.

The registry is intentionally kept inside *ice_core* so both *ice_sdk* and
*ice_cli* (higher layers) can import it without creating a circular dependency.
"""

from typing import Dict, List

from pydantic import BaseModel, Field

from .enums import ModelProvider

__all__ = [
    "LLMModelInfo",
    "list_models",
    "get_model_info",
    "is_allowed_model",
    "BANNED_MODELS",
    "DEFAULT_MODEL_ID",
    "get_default_model_id",
]

class LLMModelInfo(BaseModel):
    """Metadata for a single Large-Language Model."""

    id: str = Field(..., description="Canonical model identifier used in API calls")
    provider: ModelProvider = Field(..., description="Model provider name")
    label: str = Field(..., description="Human-friendly display label")
    best_for: str = Field(..., description="One-sentence guidance on typical use-cases")
    max_tokens: int | None = Field(
        None,
        description="Maximum tokens accepted by the model (None when unknown)",
    )

    model_config = {
        "extra": "forbid",
    }

# ---------------------------------------------------------------------------
# Registry definition -------------------------------------------------------
# ---------------------------------------------------------------------------

_ALLOWED_MODELS: Dict[str, LLMModelInfo] = {
    # OpenAI --------------------------------------------------------------
    "gpt-4": LLMModelInfo(
        id="gpt-4",
        provider=ModelProvider.OPENAI,
        label="GPT-4 (OpenAI)",
        best_for="High-quality reasoning and code generation",
        max_tokens=8192,
    ),
    "gpt-4.1": LLMModelInfo(
        id="gpt-4.1",
        provider=ModelProvider.OPENAI,
        label="GPT-4.1 (OpenAI)",
        best_for="General reasoning & code generation with high quality",
        max_tokens=128000,
    ),
    "gpt-4-turbo": LLMModelInfo(
        id="gpt-4-turbo",
        provider=ModelProvider.OPENAI,
        label="GPT-4 Turbo (OpenAI)",
        best_for="Fast GPT-4 performance with reduced cost",
        max_tokens=128000,
    ),
    "gpt-4o": LLMModelInfo(
        id="gpt-4o",
        provider=ModelProvider.OPENAI,
        label="GPT-4o (OpenAI)",
        best_for="Fastest GPT-4 tier – balanced quality & latency",
        max_tokens=128000,
    ),
    "gpt-4-turbo-2024-04-09": LLMModelInfo(
        id="gpt-4-turbo-2024-04-09",
        provider=ModelProvider.OPENAI,
        label="GPT-4 Turbo 04/2024 (OpenAI)",
        best_for="Cost-optimised GPT-4 for prod workloads",
        max_tokens=128000,
    ),
    "gpt-4.5-preview": LLMModelInfo(
        id="gpt-4.5-preview",
        provider=ModelProvider.OPENAI,
        label="GPT-4.5 Preview (OpenAI)",
        best_for="Early access to upcoming GPT-4.5 capabilities",
        max_tokens=None,
    ),
    # Anthropic -----------------------------------------------------------
    "claude-4-sonnet": LLMModelInfo(
        id="claude-4-sonnet",
        provider=ModelProvider.ANTHROPIC,
        label="Claude-4 Sonnet (Anthropic)",
        best_for="Creative writing, analytical reasoning",
        max_tokens=200000,
    ),
    "claude-4-opus": LLMModelInfo(
        id="claude-4-opus",
        provider=ModelProvider.ANTHROPIC,
        label="Claude-4 Opus (Anthropic)",
        best_for="State-of-the-art reasoning & long-context",
        max_tokens=200000,
    ),
    # Google --------------------------------------------------------------
    "gemini-2.5-pro": LLMModelInfo(
        id="gemini-2.5-pro",
        provider=ModelProvider.GOOGLE,
        label="Gemini 2.5 Pro (Google)",
        best_for="Multimodal tasks & long-context summarisation",
        max_tokens=100000,
    ),
    # DeepSeek ------------------------------------------------------------
    "deepseek-v3.1": LLMModelInfo(
        id="deepseek-v3.1",
        provider=ModelProvider.DEEPSEEK,
        label="DeepSeek V3.1",
        best_for="Large-scale code understanding & generation",
        max_tokens=None,
    ),
}

# Explicitly banned models (legacy 3.5 family and variants) -----------------
BANNED_MODELS: set[str] = {
    "gpt-3.5-turbo",
    "gpt-3.5",
    "gpt-3.5-turbo-0613",
}

# Default recommended model -------------------------------------------------
DEFAULT_MODEL_ID: str = "gpt-4-turbo-2024-04-09"

# ---------------------------------------------------------------------------
# Public helper APIs --------------------------------------------------------
# ---------------------------------------------------------------------------

def list_models() -> List[LLMModelInfo]:  # – helper
    """Return list of allowed models sorted by provider/name."""
    return sorted(_ALLOWED_MODELS.values(), key=lambda m: (m.provider.value, m.id))

def get_model_info(model_id: str) -> LLMModelInfo | None:
    """Return :class:`LLMModelInfo` for *model_id* or ``None`` if unknown."""
    return _ALLOWED_MODELS.get(model_id)

def is_allowed_model(model_id: str) -> bool:  # – helper
    """Return ``True`` when *model_id* is listed and *not* banned."""
    return model_id in _ALLOWED_MODELS and model_id not in BANNED_MODELS

def get_default_model_id() -> str:  # – helper
    """Return the project-wide default LLM model identifier."""
    return DEFAULT_MODEL_ID
