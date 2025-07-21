"""Helper factory for creating *AgentConfig* instances.

This module lives in the **SDK layer** so examples, scripts and higher-level
orchestrators can depend on it *without* introducing an import cycle towards
``ice_orchestrator``.  It provides a **single opinionated helper** that
encapsulates the most common configuration parameters used across demos.

Keeping the default values in one place avoids subtle drift between
examples, documentation and internal tests.
"""

from __future__ import annotations

from ice_sdk.models.agent_models import AgentConfig, ModelSettings

__all__ = ["AgentFactory"]


class AgentFactory:  # noqa: D101 – simple utility, not part of public stable API
    """Centralised factory for *AgentConfig* creation.

    Example
    -------
    ```python
    from ice_sdk.utils.agent_factory import AgentFactory

    cfg = AgentFactory.create_default(
        name="weather-summariser",
        instructions="Summarise the current weather given JSON data.",
    )
    ```
    """

    DEFAULT_MODEL: str = "gpt-4o"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 512
    DEFAULT_PROVIDER: str = "openai"

    @classmethod
    def create_default(cls, name: str, instructions: str) -> AgentConfig:  # noqa: D401
        """Return an :class:`AgentConfig` with project-wide defaults.

        Parameters
        ----------
        name: str
            Human-readable identifier for the agent.
        instructions: str
            System prompt / high-level instructions.

        Returns
        -------
        AgentConfig
            Config object ready to pass into :class:`ice_sdk.agents.AgentNode`.
        """

        model_settings = ModelSettings(
            model=cls.DEFAULT_MODEL,
            temperature=cls.DEFAULT_TEMPERATURE,
            max_tokens=cls.DEFAULT_MAX_TOKENS,
            provider=cls.DEFAULT_PROVIDER,
        )

        return AgentConfig(
            name=name,
            instructions=instructions,
            model=cls.DEFAULT_MODEL,
            model_settings=model_settings,
            tools=[],
        )
