"""Helper factory for creating AgentNodeConfig instances.

This module provides configuration builders for agents.

Agents execute via the orchestrator's builtin agent executor; concrete agent
implementations are registered via factories in core/registry.
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from pydantic import validate_call

from ice_core.models import AgentNodeConfig, LLMConfig, ModelProvider, ToolConfig
from ice_core.protocols.agent import IAgent
from ice_core.unified_registry import global_agent_registry

__all__ = ["AgentFactory", "agent_factory", "agent_node"]

TAgentFactory = TypeVar("TAgentFactory", bound=Callable[..., IAgent])


def agent_factory(
    name: Optional[str] = None,
    *,
    auto_register: bool = True,
) -> Callable[[TAgentFactory], TAgentFactory]:
    """Decorator to mark *factory functions* that build agents.

    Parameters
    ----------
    name : str | None
        Public registry name (defaults to the function name).
    auto_register : bool, default ``True``
        Whether to auto-register the factory with the global registry when the
        module is imported. Keep ``True`` for production code; set to ``False``
        in tests that verify registration logic manually.

    Returns
    -------
    Callable[[TAgentFactory], TAgentFactory]
        The original factory function, unmodified (besides validation wrapper).
    """

    def decorator(factory: TAgentFactory) -> TAgentFactory:  # type: ignore[name-defined]
        public_name = name or factory.__name__

        if auto_register:
            import_path = f"{factory.__module__}:{factory.__name__}"
            global_agent_registry.register_agent(public_name, import_path)

        # Attach metadata for introspection / tooling
        setattr(factory, "__agent_factory_name__", public_name)
        setattr(factory, "__agent_factory_registered__", auto_register)

        # Optional runtime arg validation via pydantic.validate_call
        validated_factory = validate_call(factory)  # type: ignore[arg-type]
        return wraps(factory)(validated_factory)  # type: ignore[return-value]

    return decorator


def agent_node(
    name: str, *, factory: Optional[str] = None, **kwargs: Any
) -> AgentNodeConfig:
    """Create an AgentNodeConfig that references a factory.

    This helper provides symmetry with `tool_node()` and enables
    factory-based agent configuration in workflows.

    Parameters
    ----------
    name : str
        The agent name (must be registered in the global agent registry).
    factory : str | None
        Factory name to use (defaults to `name`).
    **kwargs
        Additional configuration passed to AgentNodeConfig.

    Returns
    -------
    AgentNodeConfig
        Fully configured agent node ready for workflow use.
    """
    factory_name = factory or name

    # Validate the agent is registered
    if factory_name not in global_agent_registry._agents:
        from ice_core.exceptions import ValidationError

        raise ValidationError(f"Agent '{factory_name}' not found in registry")

    return AgentNodeConfig(
        id=f"agent_{name}",
        type="agent",
        package=name,  # Use agent name; executor resolves via registry
        **kwargs,
    )


class AgentFactory:
    """Centralized factory for AgentNodeConfig creation.

    Example:
        >>> from ice_builder.utils.agent_factory import AgentFactory
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
        max_retries: int = 3,
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

        return AgentNodeConfig(  # type: ignore[call-arg]
            id=f"agent_{id(system_prompt)}",  # Generate unique ID
            type="agent",
            package="default_agent",  # Resolved via agent registry
            llm_config=llm_config,
            agent_config={"system_prompt": system_prompt} if system_prompt else {},
            tools=[ToolConfig(name=tool, parameters={}) for tool in (tools or [])],  # type: ignore[arg-type]
            retries=max_retries,
        )
