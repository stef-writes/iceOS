"""
Prompt template system with version tracking

This module contains a large amount of legacy/deprecation shims that are not
executed by normal runtime paths.  Exclude from coverage calculations to avoid
penalising the coverage gate while the shims remain for backward-compatibility.
"""

from __future__ import annotations

import logging
import re

# from enum import Enum  # removed; using core enum
from typing import Any, Dict, Optional, TypeAlias
from warnings import warn

from packaging import version
from pydantic import BaseModel, ConfigDict, Field, field_validator

# pragma: no cover


logger = logging.getLogger(__name__)


import warnings as _warnings  # noqa: E402

# Use the canonical enum from core and emit deprecation warning --------------
from ice_core.models.enums import ModelProvider as _CoreModelProvider  # noqa: E402

# Re-export for backward compatibility so MyPy recognises ModelProvider attribute
ModelProvider: TypeAlias = _CoreModelProvider

_warnings.warn(
    "ice_sdk.models.config.ModelProvider is deprecated; import from ice_core.models.enums instead.",
    DeprecationWarning,
    stacklevel=2,
)


def parse_model_version(
    model_name: str, provider: ModelProvider = ModelProvider.OPENAI
) -> str:
    """Convert model name to semantic version string.

    Args:
        model_name: Name of the model (e.g., 'gpt-4', 'gpt-4-turbo')
        provider: Model provider to use for version parsing

    Returns:
        Semantic version string (e.g., '4.0.0', '4.1.0')

    Raises:
        ValueError: If model name cannot be parsed
    """
    # OpenAI models
    if provider == ModelProvider.OPENAI:
        if model_name == "gpt-4":
            return "4.0.0"
        elif model_name == "gpt-4-turbo":
            return "4.1.0"
        elif model_name == "gpt-4-turbo-2024-04-09":
            return "4.1.1"
        elif model_name == "gpt-4-32k":
            return "4.0.1"
        elif model_name == "gpt-3.5-turbo":
            return "3.5.0"
        elif model_name == "gpt-4o":
            return "4.2.0"
        elif model_name == "gpt-4.1":
            return "4.1.0"
        elif model_name == "gpt-4-1106-preview":
            return "4.1.0"
        else:
            raise ValueError(f"Unsupported OpenAI model: {model_name}")

    # Anthropic models
    elif provider == ModelProvider.ANTHROPIC:
        # Claude 4 models (newest)
        if model_name == "claude-opus-4-20250514":
            return "4.0.0"
        elif model_name == "claude-sonnet-4-20250514":
            return "4.0.0"
        # Claude 3.7 Sonnet
        elif model_name == "claude-3-7-sonnet-20250219":
            return "3.7.0"
        # Claude 3.5 models
        elif model_name == "claude-3-5-sonnet-20241022":
            return "3.5.1"
        elif model_name == "claude-3-5-sonnet-20240620":
            return "3.5.0"
        elif model_name == "claude-3-5-haiku-20241022":
            return "3.5.0"
        # Claude 3 models (original)
        elif model_name == "claude-3-opus-20240229":
            return "3.0.0"
        elif model_name == "claude-3-sonnet-20240229":
            return "3.0.0"
        elif model_name == "claude-3-haiku-20240307":
            return "3.0.0"
        # Claude 2 models
        elif model_name == "claude-2":
            return "2.0.0"
        elif model_name == "claude-2.1":
            return "2.1.0"
        else:
            raise ValueError(f"Unsupported Anthropic model: {model_name}")

    # Google models
    elif provider == ModelProvider.GOOGLE:
        if model_name == "gemini-1.0-pro-latest":
            return "1.0.0"
        elif model_name == "gemini-ultra":
            return "1.0.0"
        elif model_name == "gemini-1.5-flash-latest":
            return "1.5.0"
        else:
            raise ValueError(f"Unsupported Google model: {model_name}")

    # DeepSeek models
    elif provider == ModelProvider.DEEPSEEK:
        # DeepSeek keys might also start with sk- or be long tokens.
        # For now, we'll be permissive.
        return "1.0.0"

    # Custom provider
    elif provider == ModelProvider.CUSTOM:
        # For custom providers, we'll assume the version is in the model name
        # or return a default version
        return "1.0.0"

    raise ValueError(f"Unsupported provider: {provider}")


class _LegacyMessageTemplate(BaseModel):
    """Template for message generation"""

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

    def format(self, **kwargs: Any) -> str:
        """Format template with provided values, using defaults for missing keys"""
        try:
            return self.content.format(**kwargs)
        except KeyError as e:
            # Return unformatted content if formatting fails
            print(f"Warning: Missing template key {e}, using unformatted content")
            return self.content

    model_config = ConfigDict(extra="forbid")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate message role"""
        valid_roles = ["system", "user", "assistant"]
        if v not in valid_roles:
            raise ValueError(f"Invalid role. Valid roles: {', '.join(valid_roles)}")
        return v

    @field_validator("version")
    @classmethod
    def validate_version_format(cls, v: str) -> str:
        """Validate version format"""
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError("Version must use semantic format (e.g., 1.2.3)")
        return v

    @field_validator("min_model_version")
    @classmethod
    def validate_model_version(cls, v: str, info: Any) -> str:
        """Validate model version"""
        provider = info.data.get("provider", ModelProvider.OPENAI)
        try:
            parse_model_version(v, provider)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid model version for provider {provider}: {str(e)}")

    def is_compatible_with_model(
        self, model_name: str, provider: ModelProvider = ModelProvider.OPENAI
    ) -> bool:
        """Check if template is compatible with given model version.

        Args:
            model_name: Name of the model to check compatibility with
            provider: Model provider to use for version checking

        Returns:
            True if model meets minimum version requirement, False otherwise
        """
        try:
            model_ver = version.parse(parse_model_version(model_name, provider))
            min_ver = version.parse(
                parse_model_version(self.min_model_version, self.provider)
            )
            return model_ver >= min_ver
        except ValueError:
            return False

    def __init__(self, **data: Any):  # type: ignore[override]
        super().__init__(**data)
        # Validate model version compatibility during initialization
        if not self.is_compatible_with_model(
            data.get("min_model_version", "gpt-4"),
            data.get("provider", ModelProvider.OPENAI),
        ):
            raise ValueError(
                f"Model {data.get('min_model_version')} is too old for this template"
            )


# NOTE: LLMConfig will move to ice_core.models in a future release.
# For now we keep it here to avoid breaking call-sites – only emit warning once.

warn(
    "ice_sdk.models.config.ModelProvider is deprecated; import from ice_core.models.enums in v1.",
    DeprecationWarning,
    stacklevel=2,
)


class _LegacyLLMConfig(BaseModel):
    """Configuration for language models"""

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

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: Optional[str], info: Any) -> Optional[str]:
        """Validate API key format based on provider."""
        provider = info.data.get("provider", ModelProvider.OPENAI)
        if v is None:
            # Allow missing api_key (will be loaded from env)
            return v
        if not v:  # All providers require an API key if provided
            raise ValueError(f"API key for provider {provider.value} cannot be empty.")
        # Allow test keys for any provider
        if v.startswith("test-"):
            return v
        if provider == ModelProvider.OPENAI:
            if not (v.startswith("sk-") and len(v) == 51) and not v.startswith(
                "sk-proj-"
            ):
                logger.warning(
                    "OpenAI API key does not match standard formats (sk-..., sk-proj-...). Proceeding, but please verify."
                )
        elif provider == ModelProvider.ANTHROPIC:
            if not v.startswith("sk-ant-"):
                logger.warning(
                    "Anthropic API key does not start with 'sk-ant-'. Proceeding, but please verify."
                )
        elif provider == ModelProvider.GOOGLE:
            if len(v) < 30:
                logger.warning(
                    "Google (Gemini) API key seems short. Proceeding, but please verify."
                )
        elif provider == ModelProvider.DEEPSEEK:
            if not v.startswith("sk-"):
                logger.warning(
                    "DeepSeek API key does not start with 'sk-'. Proceeding, but please verify its format."
                )
        elif provider == ModelProvider.CUSTOM:
            pass
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str, info: Any) -> str:
        """Validate model name based on provider."""
        provider = info.data.get("provider", ModelProvider.OPENAI)
        try:
            parse_model_version(v, provider)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid model for provider {provider}: {str(e)}")


# Legacy class retained for schema generation; do **not** use in new code.
class _LegacyAppConfig(BaseModel):
    """Application configuration"""

    version: str = Field(..., description="Application version")
    environment: str = Field("development", description="Runtime environment")
    debug: bool = Field(False, description="Debug mode flag")
    api_version: str = Field("v1", description="API version")
    log_level: str = Field("INFO", description="Logging level")

    model_config = ConfigDict(extra="forbid")

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format"""
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError("Version must use semantic format (e.g., 1.2.3)")
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting"""
        valid_envs = ["development", "testing", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(
                f"Invalid environment. Valid options: {', '.join(valid_envs)}"
            )
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(
                f"Invalid log level. Valid options: {', '.join(valid_levels)}"
            )
        return v


# ---------------------------------------------------------------------------
# Alias to core domain model (preferred)
# ---------------------------------------------------------------------------

import warnings as _warnings  # noqa: E402

from ice_core.models.app_config import AppConfig as AppConfig  # noqa: E402, F401
from ice_core.models.llm import LLMConfig as LLMConfig  # noqa: E402, F401
from ice_core.models.llm import MessageTemplate as MessageTemplate  # noqa: E402

_warnings.warn(
    "ice_sdk.models.config.AppConfig is deprecated; import from ice_core.models.app_config instead.",
    DeprecationWarning,
    stacklevel=2,
)
