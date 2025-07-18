"""Agent models."""

from typing import Any, List, Literal, Optional, Type  # noqa: I001

from pydantic import BaseModel, Field

from ..skills.base import SkillBase  # Updated from BaseTool


class ModelSettings(BaseModel):
    """Model settings for agents."""

    model: str = Field(..., description="Model name (e.g., gpt-4)")
    temperature: float = Field(0.7, description="Model temperature")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    provider: str = Field("openai", description="Model provider")


class AgentConfig(BaseModel):
    """Configuration for an agent."""

    name: str = Field(..., description="Agent name")
    instructions: str = Field(..., description="Agent instructions")
    model: str = Field(..., description="Model name")
    model_settings: ModelSettings = Field(..., description="Model settings")
    tools: List[SkillBase] = Field(default_factory=list, description="Available tools")
    output_type: Optional[Type[BaseModel]] = Field(None, description="Output type")

    # ------------------------------------------------------------------
    # Experimental v2 knobs (2025-06) -----------------------------------
    # ------------------------------------------------------------------
    max_rounds: int = Field(
        2, ge=1, description="Maximum planning rounds the agent is allowed to perform."
    )
    budget_usd: Optional[float] = Field(
        None,
        gt=0,
        description="Stop execution when the projected cost exceeds this budget.",
    )
    memory_enabled: bool = Field(
        False, description="Enable persistence of context between invocations."
    )
    memory_window: int = Field(
        8,
        ge=1,
        description="Number of dialog exchanges (user+assistant) to retain in memory.",
    )
    failure_policy: Literal["retry", "skip", "abort"] = Field(
        "abort", description="Behaviour when a tool or LLM call fails."
    )
    concurrency: int = Field(
        1, ge=1, description="Maximum number of tool calls executed concurrently."
    )

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
    }


class InputGuardrail(BaseModel):
    """Schema and validation rules for agent inputs.

    This minimal implementation is *intentionally* lightweight – the public
    SDK surface only requires that the class exists and can be instantiated.
    Future iterations may add richer, rule-based validation.
    """

    rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Validation rules expressed as an arbitrary JSON-serialisable structure",
    )

    # ------------------------------------------------------------------
    # Public validation hook -------------------------------------------
    # ------------------------------------------------------------------
    def validate(self, data: Any) -> bool:  # type: ignore[override]
        """Validate *data* against the guardrail rules.

        The default implementation performs a *very* lightweight check:

        *   When *rules* is an empty mapping the method always returns *True*.
        *   When *rules* contains ``required`` (list[str]) we verify that all
            listed keys are present in *data* when the latter is a mapping.

        More sophisticated rule engines (JSON Schema, JMESPath, etc.) can be
        plugged-in later without changing the public interface.
        """

        if not self.rules:
            return True

        required = self.rules.get("required")
        if required and isinstance(data, dict):
            missing = [key for key in required if key not in data]
            if missing:
                return False

        # Fallback – assume unknown rules are satisfied ------------------
        return True


class OutputGuardrail(BaseModel):
    """Schema and validation rules for agent outputs.

    Mirrors :class:`InputGuardrail` but for the *output* side.
    """

    rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Validation rules expressed as an arbitrary JSON-serialisable structure",
    )

    def validate(self, data: Any) -> bool:  # type: ignore[override]
        """Validate *data* produced by the agent.

        Mirrors :meth:`InputGuardrail.validate` but operates on *output*
        payloads.  The default behaviour is identical – subclasses can extend
        it with additional logic (range checks, JSON Schema, etc.).
        """

        if not self.rules:
            return True

        # Example: enforce allowed_keys subset ---------------------------
        allowed = self.rules.get("allowed")
        if allowed and isinstance(data, dict):
            extra = [k for k in data.keys() if k not in allowed]
            if extra:
                return False

        return True
