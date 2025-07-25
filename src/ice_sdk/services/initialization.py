"""Service initialization for iceOS SDK.

This module provides a clean initialization interface that sets up all
required services without violating layer boundaries.
"""

from ice_sdk.services.locator import ServiceLocator


def initialize_services() -> None:
    """Initialize all SDK services.
    
    This function should be called once during application startup to ensure
    all services are properly registered and available through ServiceLocator.
    
    Example:
        >>> from ice_sdk.services.initialization import initialize_services
        >>> initialize_services()
        >>> # Now all services are available through ServiceLocator
        >>> workflow_service = ServiceLocator.get("workflow_service")
    """
    # NOTE: The orchestrator layer is responsible for its own initialization.
    # SDK should not depend on orchestrator.
    
    # Initialize SDK services
    try:
        from ice_sdk.services.builder_service import BuilderService
        ServiceLocator.register("builder_service", BuilderService())
    except ImportError:
        pass
    
    try:
        from ice_sdk.services.llm_adapter import LLMServiceAdapter
        ServiceLocator.register("llm_service", LLMServiceAdapter())
    except ImportError:
        pass
    
    # Initialize agent registry
    try:
        from ice_sdk.services.agent_registry_init import initialize_agent_registry
        initialize_agent_registry()
    except ImportError:
        pass


__all__ = ["initialize_services"] 