"""Shared exception & error-code hierarchy for iceOS core packages.

Adding a thin but expressive hierarchy makes it easier to:
* Attach stable machine-readable codes to errors (monitoring/alerting)
* Preserve the original error message/context
* Avoid a proliferation of bespoke exception classes

IMPORTANT: Keep the dependency footprint minimal – no external imports.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Optional

__all__ = [
    "ErrorCode",
    "CoreError",
    "CycleDetectionError",
    "MCPTransportError",
]


class ErrorCode(IntEnum):
    """Stable error codes for high-level failure classes."""

    CYCLIC_TOOL_COMPOSITION = 1001
    MCP_TRANSPORT_FAILURE = 1101

    # Generic fall-back
    UNKNOWN = 9000

    def describe(self) -> str:  # noqa: D401
        """Return human-readable description."""
        mapping = {
            ErrorCode.CYCLIC_TOOL_COMPOSITION: "Cyclic tool/agent invocation detected",
            ErrorCode.MCP_TRANSPORT_FAILURE: "Secure transport failure while communicating with MCP server",
            ErrorCode.UNKNOWN: "Unknown or uncategorised error",
        }
        return mapping.get(self, mapping[ErrorCode.UNKNOWN])


class CoreError(RuntimeError):
    """Base class for all custom iceOS errors.

    Args:
        code: Machine-readable :class:`ErrorCode`
        message: Human-readable explanation (optional – will default to :pyattr:`ErrorCode.describe`)
        payload: Optional additional data to attach to the error for programmatic handling.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        *,
        payload: Any | None = None,
    ):
        self.code = code
        self.payload = payload
        super().__init__(message or code.describe())


class CycleDetectionError(CoreError):
    """Raised when an agent–tool cycle is detected at runtime."""

    def __init__(self, cycle_path: str):
        super().__init__(
            ErrorCode.CYCLIC_TOOL_COMPOSITION,
            f"Cyclic agent–tool invocation detected: {cycle_path}",
            payload={"cycle": cycle_path},
        )


class MCPTransportError(CoreError):
    """Raised when encrypted transport with the MCP server fails."""

    def __init__(self, original_exc: Exception):
        super().__init__(
            ErrorCode.MCP_TRANSPORT_FAILURE,
            f"Secure MCP transport failed: {original_exc}",
            payload={"exc": original_exc},
        )
