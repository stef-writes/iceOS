from __future__ import annotations

from typing import Any, Callable, Dict

from pydantic import BaseModel

from ice_core.models import LLMConfig, ModelProvider

# ----------------------------------------
# Cost-tracking decorator
from ice_core.costs import cost_checkpoint

# ----------------------------------------
# LLM operator helpers -------------------------------------------------------
# ----------------------------------------

@cost_checkpoint  # type: ignore[misc]
def llm_operator(func: Callable[..., Any]) -> Callable[..., Any]:
    """Marker decorator for LLM operator functions (currently a no-op)."""
    return func


class LLMOperatorConfig(BaseModel):
    """Configuration for LLM operators.
    
    NOTE: This is NOT the same as ice_core.models.node_models.LLMOperatorConfig!
    This is a simpler configuration used by SDK operators, while the one in
    ice_core is a full workflow node configuration.
    
    This config is used by LLMOperator subclasses like SummarizerOperator,
    InsightsOperator, etc. for their internal operation.
    """

    provider: ModelProvider = ModelProvider.OPENAI
    model: str = "gpt-4-turbo"
    temperature: float = 0.7
    max_tokens: int = 1024
    prompt: str = ""

    # Allow BaseOperatorConfig to pass extra fields
    class Config:  # type: ignore[misc]
        extra = "allow"


class LLMOperator(BaseModel):
    """Base class for LLM operators with chain execution capabilities."""

    config: LLMOperatorConfig
    llm_service: Any = None  # Will be initialized in subclasses

    async def process(self, input_data: str) -> str:
        """Process input data through the LLM.

        Args:
            input_data: Input string to process

        Returns:
            Processed output string
        """
        # Import here to avoid circular dependencies
        from ice_core.llm.service import LLMService

        llm_config = LLMConfig(
            provider=self.config.provider,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        llm_service = LLMService()
        response = await llm_service.generate(
            prompt=self.config.prompt.format(input=input_data), config=llm_config
        )

        return response["content"]

    async def generate(self, prompt: str) -> str:
        """Generate text using the LLM service.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            Generated text response
        """
        llm_config = LLMConfig(
            provider=self.config.provider,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        
        response = await self.llm_service.generate(prompt=prompt, config=llm_config)
        return response["content"]

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the operator with given inputs.

        Args:
            inputs: Input dictionary

        Returns:
            Output dictionary with processed results
        """
        input_data = inputs.get("input", "")
        result = await self.process(input_data)
        return {"output": result}
