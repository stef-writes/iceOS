from typing import Any
from fastapi import Request

from ice_sdk.tools.service import ToolService

def get_tool_service(request: Request) -> ToolService:
    """Return the application-wide ToolService stored in `app.state`."""
    return request.app.state.tool_service  # type: ignore[attr-defined,no-any-return]

def get_context_manager(request: Request) -> Any:
    """Return the shared context manager stored in `app.state`.
    
    Note: Using Any type to avoid layer boundary violation.
    The actual type is GraphContextManager from ice_orchestrator.
    """
    return request.app.state.context_manager  # type: ignore[attr-defined,no-any-return]
