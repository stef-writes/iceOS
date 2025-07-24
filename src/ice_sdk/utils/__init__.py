"""Utility helpers (logging, error handling, etc.) shared by ice_* packages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ice_core.utils.logging import logger, setup_logger  # re-export
from ice_core.utils.security import sanitize_path
from ice_core.utils.text import TextProcessor  # re-export

if TYPE_CHECKING:
    from ice_core.utils.coercion import coerce_types
    from ice_sdk.utils.token_counter import TokenCounter

__all__ = [
    "logger",
    "setup_logger",
    "TokenCounter",
    "coerce_types",
    "sanitize_path",
    "TextProcessor",
]
