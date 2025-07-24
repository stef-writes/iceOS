"""Helper factory for creating AgentNodeConfig instances.

This module lives in the SDK layer so examples, scripts and higher-level
orchestrators can depend on it without introducing an import cycle.
"""

from __future__ import annotations

from ice_core.models import AgentNodeConfig, LLMConfig, ModelProvider

__all__ = ["AgentFactory"]

class AgentFactory:
    """Centralized factory for AgentNodeConfig creation.

    Example:
        >>> from ice_sdk.utils.agent_factory import AgentFactory
        >>> cfg = AgentFactory.create_default(
        ...     system_prompt="You are a helpful assistant.",
        ...     tools=["search_tool", "calculator"]
        ... )
    """

    DEFAULT_MODEL: str = "gpt-4"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 512
    DEFAULT_PROVIDER: ModelProvider = ModelProvider.OPENAI

    @classmethod
    def create_default(
        cls, 
        system_prompt: str,
        tools: list[str] | None = None,
        model: str | None = None,
        max_retries: int = 3
    ) -> AgentNodeConfig:
        """Create an AgentNodeConfig with project-wide defaults.

        Args:
            system_prompt: Base system prompt for the agent
            tools: List of allowed tool names (optional)
            model: Model to use (defaults to DEFAULT_MODEL)
            max_retries: Maximum retry attempts (defaults to 3)

        Returns:
            AgentNodeConfig ready to pass to AgentNode
        """
        llm_config = LLMConfig(
            provider=cls.DEFAULT_PROVIDER,
            model=model or cls.DEFAULT_MODEL,
            temperature=cls.DEFAULT_TEMPERATURE,
            max_tokens=cls.DEFAULT_MAX_TOKENS,
        )

        return AgentNodeConfig(
            llm_config=llm_config,
            system_prompt=system_prompt,
            tools=tools or [],
            max_retries=max_retries,
        )
