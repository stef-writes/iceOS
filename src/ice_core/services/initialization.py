"""Service initialization for iceOS SDK.

This module ensures the SDK is properly initialized with minimal setup.
All runtime services are handled by the orchestrator.
"""



def initialize_sdk() -> None:
    """Initialize the SDK layer.
    
    This performs minimal initialization:
    - Imports tool packages to trigger @tool decorator registration
    - Sets up the ServiceLocator for accessing orchestrator services
    
    All runtime services (workflow execution, tool execution, context management)
    are handled by the orchestrator layer.
    """
    import os
    profile = os.getenv("ICEOS_PROFILE", "dev")

    # No concrete tool packages yet – will be imported automatically once toolkits are implemented.
    
    # TODO: remove this stub once first-party toolkits are available.
    
    # That's it! All runtime services are in orchestrator 