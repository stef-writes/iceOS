"""Service locator pattern implementation for iceOS.

This module provides a minimalist global registry for cross-cutting services
that need to be accessed across layer boundaries without creating circular
dependencies.

The ServiceLocator pattern allows the orchestrator layer to register concrete
implementations that the SDK layer can use without directly importing from
higher layers.

Example:
    >>> from ice_sdk.services import ServiceLocator
    >>> # Register a service (typically done during initialization)
    >>> ServiceLocator.register("my_service", MyServiceImpl())
    >>> # Get the service elsewhere
    >>> service = ServiceLocator.get("my_service")
"""

from __future__ import annotations

from threading import Lock
from typing import Any, Dict, Optional, Type

__all__: list[str] = [
    "ServiceLocator",
    "get_workflow_proto",
]

def get_workflow_proto() -> Type[Any]:
    """Return the Workflow concrete class registered by the orchestrator layer.

    To respect the onion-architecture boundary, the SDK layer must not
    import ice_orchestrator directly. Instead, the concrete implementation
    is provided at runtime by the orchestrator layer via ServiceLocator.

    Returns:
        The Workflow class registered under "workflow_proto"
        
    Raises:
        KeyError: When the orchestrator layer failed to register the workflow
            implementation. Downstream callers should catch this and fail
            fast with a helpful message.
            
    Example:
        >>> try:
        ...     Workflow = get_workflow_proto()
        ...     workflow = Workflow(nodes=[], edges=[])
        ... except KeyError:
        ...     raise RuntimeError("Orchestrator not initialized")
    """
    return ServiceLocator.get("workflow_proto")


class ServiceLocator:
    """Global service registry for dependency injection across layers.
    
    This class provides a thread-safe way to register and retrieve services
    without creating tight coupling between layers. Services are registered
    by name and can be retrieved from anywhere in the codebase.
    
    Common services registered:
        - "workflow_proto": The Workflow class from orchestrator
        - "workflow_service": IWorkflowService implementation
        - "tool_service": ToolService instance
        - "context_manager": GraphContextManager instance
        - "llm_service": LLMService instance
    """
    
    _services: Dict[str, Any] = {}
    _lock = Lock()
    
    @classmethod
    def register(cls, name: str, service: Any) -> None:
        """Register a service by name.
        
        Args:
            name: Unique identifier for the service
            service: The service instance or class to register
            
        Note:
            If a service with the same name already exists, it will be
            silently replaced. This allows for test doubles and
            re-initialization.
        """
        with cls._lock:
            cls._services[name] = service
    
    @classmethod
    def get(cls, name: str) -> Optional[Any]:
        """Retrieve a registered service by name.
        
        Args:
            name: The service identifier used during registration
            
        Returns:
            The registered service instance/class, or None if not found
            
        Example:
            >>> tool_service = ServiceLocator.get("tool_service")
            >>> if tool_service:
            ...     tools = tool_service.available_tools()
        """
        with cls._lock:
            return cls._services.get(name)
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered services.
        
        This is primarily useful for testing to ensure a clean state
        between test cases.
        """
        with cls._lock:
            cls._services.clear()
