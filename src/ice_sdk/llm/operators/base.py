from __future__ import annotations

from typing import Any, Callable, ParamSpec, TypeVar, Dict

from pydantic import BaseModel

from ice_core.models import LLMConfig, ModelProvider

from functools import wraps

# ----------------------------------------
# Optional cost-tracking decorator – gracefully degrade when unavailable ----

P = ParamSpec("P")
R = TypeVar("R")

# Robust no-op decorator that supports optional keyword/positional arguments
def _noop_decorator(*d_args: Any, **d_kwargs: Any):  # noqa: D401 – flexible shim
    """Return *func* unchanged regardless of how the decorator is invoked.

    Handles both parameterless ``@decorator`` and parametrised ``@decorator(x=1)``
    invocations so that call-sites remain syntactically valid even when the
    real implementation is unavailable at import-time (e.g., during unit
    tests without the optional *cost* module).
    """

    if d_args and callable(d_args[0]) and len(d_args) == 1 and not d_kwargs:
        # Used as plain @decorator -----------------------------------------
        func = d_args[0]
        return func  # type: ignore[return-value]

    # Used as @decorator(key=value) – return wrapper factory ----------------
    def _inner(func: Callable[P, R]) -> Callable[P, R]:  # noqa: D401
        @wraps(func)
        def _wrapped(*args: P.args, **kwargs: P.kwargs):  # type: ignore[misc]
            return func(*args, **kwargs)

        return _wrapped  # type: ignore[return-value]

    return _inner

# Try importing the real cost decorator; fall back to no-op shim ------------
try:
    from ice_sdk.providers.costs import cost_checkpoint  # type: ignore[import]
except ImportError:
    cost_checkpoint = _noop_decorator

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
        from ice_sdk.providers.llm_service import LLMService

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
