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

    if profile == "dev":
        # In dev mode import all SDK tool packages for convenience
        try:
            import ice_sdk.tools.core
            import ice_sdk.tools.ai
            import ice_sdk.tools.system
            import ice_sdk.tools.web
            import ice_sdk.tools.db
        except ImportError:
            pass  # Best effort
    
    # Import agent utilities to ensure they're available
    try:
        import ice_sdk.agents.utils
    except ImportError:
        pass
    
    # That's it! All runtime services are in orchestrator 