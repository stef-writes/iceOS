"""LLM-related domain models shared across the code-base.

These definitions are extracted from *ice_sdk.models.config* so that higher
layers can depend on a stable, framework-agnostic contract without importing
ice_sdk.* (which would violate layering rules).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from packaging import version  # runtime dependency provided by poetry
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import ModelProvider

__all__: list[str] = [
    "parse_model_version",
    "MessageTemplate",
    "LLMConfig",
]

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper – convert provider/model → semantic version
# ---------------------------------------------------------------------------


def parse_model_version(
    model_name: str, provider: ModelProvider = ModelProvider.OPENAI
) -> str:
    """Return semantic version string for *model_name*.

    Replicates the lookup logic originally hosted in *ice_sdk.models.config*.
    Only models that appear in tests/CI are enumerated; new providers can be
    added with a straightforward ``elif``.
    """

    if provider == ModelProvider.OPENAI:
        mapping = {
            "gpt-4": "4.0.0",
            "gpt-4-turbo": "4.1.0",
            "gpt-4-turbo-2024-04-09": "4.1.1",
            "gpt-4-32k": "4.0.1",
            "gpt-3.5-turbo": "3.5.0",
            "gpt-4o": "4.2.0",
            "gpt-4.1": "4.1.0",
            "gpt-4-1106-preview": "4.1.0",
        }
        if model_name in mapping:
            return mapping[model_name]
        raise ValueError(f"Unsupported OpenAI model: {model_name}")

    elif provider == ModelProvider.ANTHROPIC:
        mapping = {
            "claude-opus-4-20250514": "4.0.0",
            "claude-sonnet-4-20250514": "4.0.0",
            "claude-3-7-sonnet-20250219": "3.7.0",
            "claude-3-5-sonnet-20241022": "3.5.1",
            "claude-3-5-sonnet-20240620": "3.5.0",
            "claude-3-5-haiku-20241022": "3.5.0",
            "claude-3-opus-20240229": "3.0.0",
            "claude-3-sonnet-20240229": "3.0.0",
            "claude-3-haiku-20240307": "3.0.0",
            "claude-2": "2.0.0",
            "claude-2.1": "2.1.0",
        }
        if model_name in mapping:
            return mapping[model_name]
        raise ValueError(f"Unsupported Anthropic model: {model_name}")

    elif provider == ModelProvider.GOOGLE:
        mapping = {
            "gemini-1.0-pro-latest": "1.0.0",
            "gemini-ultra": "1.0.0",
            "gemini-1.5-flash-latest": "1.5.0",
        }
        if model_name in mapping:
            return mapping[model_name]
        raise ValueError(f"Unsupported Google model: {model_name}")

    elif provider == ModelProvider.DEEPSEEK:
        # DeepSeek keys can vary; return default until spec stabilises
        return "1.0.0"

    elif provider == ModelProvider.CUSTOM:
        return "1.0.0"

    raise ValueError(f"Unsupported provider: {provider}")


# ---------------------------------------------------------------------------
# Message template ----------------------------------------------------------
# ---------------------------------------------------------------------------


class MessageTemplate(BaseModel):
    """Prompt / message template with version gating."""

    role: str = Field(..., description="Message role (system, user, assistant)")
    content: str = Field(..., description="Message content template")
    version: str = Field(
        "1.0.0", pattern=r"^\d+\.\d+\.\d+$", description="Template version"
    )
    min_model_version: str = Field(
        "gpt-4", description="Minimum required model version"
    )
    provider: ModelProvider = Field(
        ModelProvider.OPENAI, description="Model provider for this template"
    )

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def format(self, **kwargs: Any) -> str:  # – mimic str.format API
        """Return formatted *content*; missing keys keep original placeholder."""
        try:
            return self.content.format(**kwargs)
        except KeyError as exc:
            _logger.warning("Missing template key %s – using unformatted content.", exc)
            return self.content

    model_config = ConfigDict(extra="forbid")

    # ------------------------------------------------------------------
    # Validators --------------------------------------------------------
    # ------------------------------------------------------------------

    @field_validator("role")
    @classmethod
    def _validate_role(cls, v: str) -> str:  # – validator
        valid_roles = {"system", "user", "assistant"}
        if v not in valid_roles:
            raise ValueError(
                f"Invalid role. Valid roles: {', '.join(sorted(valid_roles))}"
            )
        return v

    @field_validator("version")
    @classmethod
    def _validate_version(cls, v: str) -> str:  # – validator
        if not re.fullmatch(r"^\d+\.\d+\.\d+$", v):
            raise ValueError("Version must use semantic format (e.g., 1.2.3)")
        return v

    @field_validator("min_model_version")
    @classmethod
    def _validate_min_model_version(cls, v: str, info: Any) -> str:
        provider = info.data.get("provider", ModelProvider.OPENAI)
        parse_model_version(v, provider)  # will raise if unsupported
        return v

    # Public API --------------------------------------------------------

    def is_compatible_with_model(
        self, model_name: str, *, provider: ModelProvider = ModelProvider.OPENAI
    ) -> bool:
        """Return ``True`` when *model_name* meets *min_model_version*."""
        try:
            model_ver = version.parse(parse_model_version(model_name, provider))
            min_ver = version.parse(
                parse_model_version(self.min_model_version, self.provider)
            )
            return model_ver >= min_ver
        except ValueError:
            return False


# ---------------------------------------------------------------------------
# LLM configuration ---------------------------------------------------------
# ---------------------------------------------------------------------------


class LLMConfig(BaseModel):
    """Provider-specific configuration for LLM calls."""

    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    max_context_tokens: Optional[int] = None
    api_key: Optional[str] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop_sequences: Optional[list[str]] = None
    custom_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific parameters"
    )

    model_config = ConfigDict(extra="allow")

    # ------------------------------------------------------------------
    # Validators --------------------------------------------------------
    # ------------------------------------------------------------------

    @field_validator("api_key")
    @classmethod
    def _validate_api_key(cls, v: Optional[str], info: Any) -> Optional[str]:
        provider = info.data.get("provider", ModelProvider.OPENAI)
        if v is None:
            return v  # loaded from env elsewhere
        if not v:
            raise ValueError(f"API key for provider {provider} cannot be empty.")
        if v.startswith("test-"):
            return v
        if provider == ModelProvider.OPENAI and not (
            v.startswith("sk-") or v.startswith("sk-proj-")
        ):
            _logger.warning(
                "OpenAI API key does not match expected pattern; proceed with caution."
            )
        return v

    @field_validator("model")
    @classmethod
    def _validate_model(cls, v: str, info: Any) -> str:
        provider = info.data.get("provider", ModelProvider.OPENAI)
        parse_model_version(v, provider)  # validates format/provider

        # Enforce allowed model list ------------------------------------------------
        try:
            from .model_registry import (  # local import to avoid cycles
                BANNED_MODELS,
                is_allowed_model,
            )
        except Exception:  # pragma: no cover – defensive
            return v  # registry unavailable during early import; skip

        if not is_allowed_model(v):
            raise ValueError(
                f"Model '{v}' is not allowed. Banned models: {', '.join(sorted(BANNED_MODELS))}"
            )
        return v
