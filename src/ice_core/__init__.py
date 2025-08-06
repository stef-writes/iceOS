"""Core, framework-agnostic domain layer for iceOS.

This package SHOULD contain *only* pure, side-effect-free business-domain
objects: dataclasses / pydantic models, stateless services, policies and
exceptions.  It MUST NOT import from any higher layer such as ``app`` or
``ice_sdk``.

Example
-------
>>> from ice_core.exceptions import CoreError
>>> raise CoreError("This feature is unavailable")
"""

from __future__ import annotations

__all__: list[str] = [
    "exceptions",
    "memory",
    "unified_registry",
    "validation",

    "toolkits",
]

from . import exceptions  # import after __all__ definition
from . import memory, toolkits, unified_registry, validation
