"""Core-level abstractions for LLM Operators.

This sub-package deliberately contains *no* concrete side-effectful code –
it only exposes the shared base classes and helper decorators that higher
layers (tools, orchestrator, plugins) build upon.
"""

from .base import LLMOperator, LLMOperatorConfig, llm_operator

__all__: list[str] = [
    "LLMOperatorConfig",
    "LLMOperator",
    "llm_operator",
]
