from __future__ import annotations

"""Compatibility wrapper around the shared DraftState definitions.

The authoritative implementation now lives in *ice_core.models.draft* so that
both author-time tooling (ice_builder) and the API layer can depend on it
without violating layer-boundary rules.
"""

from ice_core.models.draft import RedisDraftStore  # type: ignore
from ice_core.models.draft import DraftState, DraftStore, InMemoryDraftStore

__all__ = [
    "DraftState",
    "DraftStore",
    "InMemoryDraftStore",
    "RedisDraftStore",
]
