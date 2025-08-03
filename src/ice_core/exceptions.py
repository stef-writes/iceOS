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
    "LayerViolationError",
    "SecurityViolationError",
    "RegistryError",
    "ValidationError",
    "DimensionMismatchError",
]

class ErrorCode(IntEnum):
    """Stable error codes for high-level failure classes."""

    CYCLIC_TOOL_COMPOSITION = 1001
    LAYER_VIOLATION = 1002  # New – layer boundary breach
    PATH_SECURITY_VIOLATION = 1003  # Unsafe path outside project root
    SCAFFOLD_VALIDATION = 1004  # Scaffolded content failed schema validation
    DIMENSION_MISMATCH = 1005  # Vector dimension mismatch

    # Generic fall-back
    UNKNOWN = 9000

    def describe(self) -> str:
        """Return human-readable description."""
        mapping = {
            ErrorCode.CYCLIC_TOOL_COMPOSITION: "Cyclic tool/agent invocation detected",
            ErrorCode.LAYER_VIOLATION: "Layer boundary violation detected",
            ErrorCode.UNKNOWN: "Unknown or uncategorised error",
            ErrorCode.DIMENSION_MISMATCH: "Vector embedding dimension mismatch",
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

# ----------------------------------------
#  Layer boundary violation --------------------------------------------------
# ----------------------------------------

class LayerViolationError(CoreError):
    """Raised when lower-layer code imports or uses forbidden higher-layer modules."""

    def __init__(self, message: str):  # – thin wrapper
        super().__init__(ErrorCode.LAYER_VIOLATION, message)


class SecurityViolationError(Exception):
    """Raised when a security violation is detected."""
    
    def __init__(self, message: str):
        super().__init__(f"Security violation: {message}")

class ScaffoldValidationError(CoreError):
    """Raised when generated scaffold fails JSON schema validation."""

    def __init__(self, details: Any | None = None):
        super().__init__(
            ErrorCode.SCAFFOLD_VALIDATION,
            "Scaffolded resource failed schema validation",
            payload=details,
        )


class ValidationError(CoreError):
    """Raised when input or output validation fails."""

    def __init__(self, message: str, *, payload: Any | None = None):
        super().__init__(ErrorCode.UNKNOWN, message, payload=payload)


class DimensionMismatchError(CoreError):
    """Raised when vector dimensionality does not match index specification."""

    def __init__(self, expected: int, actual: int):
        super().__init__(
            ErrorCode.DIMENSION_MISMATCH,
            f"Embedding dimension mismatch: expected {expected}, got {actual}",
            payload={"expected": expected, "actual": actual},
        )


class RegistryError(Exception):
    """Raised when registry operations fail."""
    
    def __init__(self, message: str):
        super().__init__(f"Registry error: {message}")
