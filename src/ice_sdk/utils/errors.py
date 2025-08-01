"""SDK-specific error types."""

from typing import Any, Dict, Optional

from ice_core.exceptions import CoreError


class ToolExecutionError(CoreError):
    """Raised when a tool fails during execution."""

    def __init__(
        self,
        tool_name: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        from ice_core.exceptions import ErrorCode

        # Use a generic tool error code
        super().__init__(ErrorCode.UNKNOWN, f"Tool '{tool_name}' failed: {message}")
        self.tool_name = tool_name
        self.details = details or {}


class AgentError(CoreError):
    """Base error for agent-related failures."""

    pass


class AgentTimeoutError(AgentError):
    """Raised when an agent exceeds its execution timeout."""

    pass


__all__ = [
    "ToolExecutionError",
    "AgentError",
    "AgentTimeoutError",
]
