"""Application/runtime configuration domain model."""

from __future__ import annotations

import re
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__: list[str] = [
    "AppConfig",
]


class AppConfig(BaseModel):
    """Top-level application configuration shared across layers."""

    version: str = Field(..., description="Application semantic version")
    environment: str = Field("development", description="Runtime environment")
    debug: bool = Field(False, description="Debug mode flag")
    api_version: str = Field("v1", description="API version exposed by HTTP APIs")
    log_level: str = Field("INFO", description="Logging level")

    # Keep Pydantic strict by forbidding unknown keys
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    # ------------------------------------------------------------------
    # Validators --------------------------------------------------------
    # ------------------------------------------------------------------

    @field_validator("version")
    @classmethod
    def _validate_version(cls, v: str) -> str:  # noqa: D401 – validator
        if not re.fullmatch(r"^\d+\.\d+\.\d+$", v):
            raise ValueError("Version must use semantic format (e.g., 1.2.3)")
        return v

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, v: str) -> str:  # noqa: D401 – validator
        valid_envs = {"development", "testing", "staging", "production"}
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(
                f"Invalid environment. Valid options: {', '.join(sorted(valid_envs))}"
            )
        return v_lower

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:  # noqa: D401 – validator
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(
                f"Invalid log level. Valid options: {', '.join(sorted(valid_levels))}"
            )
        return upper
