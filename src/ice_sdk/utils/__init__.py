"""Utility helpers (logging, error handling, etc.) shared by ice_* packages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ice_core.utils.logging import logger, setup_logger  # noqa: F401 re-export
from ice_core.utils.meta import public  # noqa: F401 re-export
from ice_core.utils.security import sanitize_path  # noqa: F401
from ice_core.utils.text import TextProcessor  # noqa: F401 re-export
from ice_sdk.utils.errors import (  # noqa: F401 re-export
    APIError,
    add_exception_handlers,
)

if TYPE_CHECKING:
    from ice_core.utils.coercion import coerce_types  # noqa: F401
    from ice_sdk.runtime.token_counter import TokenCounter  # noqa: F401

__all__ = [
    "logger",
    "setup_logger",
    "APIError",
    "add_exception_handlers",
    "TokenCounter",
    "coerce_types",
    "sanitize_path",
    "TextProcessor",
]

__all__.append("public")

# Lazy imports to avoid unnecessary dependency loading on lightweight clients.
