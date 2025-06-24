"""Capability utilities package.

Currently re-exports the :class:`~ice_sdk.capabilities.card.CapabilityCard` model
so external code can import it via ``ice_sdk.capabilities``.
"""

from .card import CapabilityCard

__all__: list[str] = [
    "CapabilityCard",
] 