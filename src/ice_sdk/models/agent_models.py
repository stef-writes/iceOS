"""Agent models."""
from typing import Any, List, Optional, Type

from pydantic import BaseModel, Field

from ..tools.base import BaseTool


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
    tools: List[BaseTool] = Field(default_factory=list, description="Available tools")
    output_type: Optional[Type[BaseModel]] = Field(None, description="Output type")

class InputGuardrail(BaseModel):
    """Schema and validation rules for agent inputs.

    This minimal implementation is *intentionally* lightweight – the public
    SDK surface only requires that the class exists and can be instantiated.
    Future iterations may add richer, rule-based validation.
    """

    rules: dict[str, Any] = Field(default_factory=dict, description="Validation rules expressed as an arbitrary JSON-serialisable structure")


class OutputGuardrail(BaseModel):
    """Schema and validation rules for agent outputs.

    Mirrors :class:`InputGuardrail` but for the *output* side.
    """

    rules: dict[str, Any] = Field(default_factory=dict, description="Validation rules expressed as an arbitrary JSON-serialisable structure") 