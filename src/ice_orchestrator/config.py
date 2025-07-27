"""Configuration management for iceOS runtime settings.

This module centralizes environment variable configuration for resource limits,
budget enforcement, and other runtime settings.
"""

import os
from typing import Optional

from pydantic import BaseModel, Field

class RuntimeConfig(BaseModel):
    """Runtime configuration loaded from environment variables."""

    # Resource limits
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens allowed per chain execution (ICE_MAX_TOKENS)",
    )
    max_depth: Optional[int] = Field(
        default=None, description="Maximum execution depth allowed (ICE_MAX_DEPTH)"
    )

    # Budget enforcement
    org_budget_usd: Optional[float] = Field(
        default=None, description="Organization budget in USD (ORG_BUDGET_USD)"
    )

    # Environment mode
    runtime_mode: str = Field(
        default="production",
        description="Runtime mode: 'production', 'development', or 'demo' (ICE_RUNTIME_MODE)",
    )

    # Budget enforcement behavior
    budget_fail_open: bool = Field(
        default=True,
        description="Whether to fail-open on budget violations in non-prod (BUDGET_FAIL_OPEN)",
    )

    # ------------------------------------------------------------------
    # Testing helpers ---------------------------------------------------
    # ------------------------------------------------------------------

    @property
    def testing_mode(self) -> bool:  # – convenience accessor
        """Return *True* when the test-suite runs with ``ICE_TESTING=1``.

        Having a single feature flag makes it easy for skills and services to
        switch to deterministic fakes instead of performing real network
        requests during the test run.  The property is **read-only** to keep
        the pydantic model immutable after instantiation.
        """

        return os.getenv("ICE_TESTING", "0") == "1"

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        """Load configuration from environment variables."""

        # Resource limits
        max_tokens = os.getenv("ICE_MAX_TOKENS")
        max_depth = os.getenv("ICE_MAX_DEPTH")

        # Budget settings
        org_budget_usd = os.getenv("ORG_BUDGET_USD")

        # Parse budget_fail_open with more flexible logic
        budget_fail_open_raw = os.getenv("BUDGET_FAIL_OPEN", "true")
        budget_fail_open = budget_fail_open_raw.lower() in ["true", "1", "yes", "on"]

        # Environment mode
        runtime_mode = os.getenv("ICE_RUNTIME_MODE", "production")

        return cls(
            max_tokens=int(max_tokens) if max_tokens else None,
            max_depth=int(max_depth) if max_depth else None,
            org_budget_usd=float(org_budget_usd) if org_budget_usd else None,
            runtime_mode=runtime_mode,
            budget_fail_open=budget_fail_open,
        )

# Global configuration instance
runtime_config = RuntimeConfig.from_env()
