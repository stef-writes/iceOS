"""Core, framework-agnostic domain layer for iceOS.

This package SHOULD contain *only* pure, side-effect-free business-domain
objects: dataclasses / pydantic models, stateless services, policies and
exceptions.  It MUST NOT import from any higher layer such as ``app`` or
``ice_sdk``.

Example
-------
>>> from ice_core.exceptions import DeprecatedError
>>> raise DeprecatedError("This feature is gone")
"""

from __future__ import annotations

__all__: list[str] = [
    "exceptions",
]

from . import exceptions  # noqa: E402, F401 import after __all__ definition
