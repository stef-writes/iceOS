from fastapi import Request

from ice_sdk import ToolService
from ice_sdk.context.manager import GraphContextManager


def get_tool_service(request: Request) -> ToolService:
    """Return the application-wide ToolService stored in `app.state`."""
    return request.app.state.tool_service  # type: ignore[attr-defined]


def get_context_manager(request: Request) -> GraphContextManager:
    """Return the shared GraphContextManager stored in `app.state`."""
    return request.app.state.context_manager  # type: ignore[attr-defined]
