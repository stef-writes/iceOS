from __future__ import annotations

"""Utility helpers (logging, error handling, etc.) shared by ice_* packages."""

from ice_sdk.utils.logging import logger, setup_logger  # noqa: F401 re-export
from ice_sdk.utils.errors import (  # noqa: F401 re-export
    APIError,
    add_exception_handlers,
)

__all__ = [
    "logger",
    "setup_logger",
    "APIError",
    "add_exception_handlers",
    "TokenCounter",
    "coerce_types",
]

# Lazy imports to avoid unnecessary dependency loading on lightweight clients.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ice_sdk.utils.token_counter import TokenCounter  # noqa: F401
    from ice_sdk.utils.type_coercion import coerce_types  # noqa: F401 