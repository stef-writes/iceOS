"""ice_core.exceptions
~~~~~~~~~~~~~~~~~~~~~~
Domain-level, typed exceptions used across layers.
"""

from __future__ import annotations


class IceCoreError(Exception):
    """Base-class for all core-layer exceptions."""


class DeprecatedError(ImportError, IceCoreError):
    """Raised when a deprecated shim or symbol is accessed in *strict* mode.

    By default, importing deprecated modules only emits a :class:`DeprecationWarning`.
    To fail hard, set the environment variable ``ICE_STRICT_SHIMS=1`` in the
    process (CI can flip this flag once all migrations are complete).
    """

    def __init__(self, message: str) -> None:  # noqa: D401 – imperative mood
        super().__init__(message)


# ---------------------------------------------------------------------------
#  Path security ----------------------------------------------------------------
# ---------------------------------------------------------------------------


class SecurityViolationError(IceCoreError):
    """Raised when a provided path escapes allowed root directory."""

    def __init__(self, path: str):  # noqa: D401 – param path only
        super().__init__(f"Illegal path traversal attempt detected: {path}")
