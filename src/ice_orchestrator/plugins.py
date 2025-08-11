from __future__ import annotations

"""Orchestrator-side plugin loader.

This module hosts the explicit registration of first-party tools to avoid
import-time side effects and keeps `ice_core` free of `ice_tools` references.
"""


def load_first_party_tools() -> int:
    """Deprecated: prefer loading via plugins.v0 manifests.

    Kept for API stability; returns 0.
    """
    return 0
