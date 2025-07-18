"""Service interfaces for *ice_core*.

Currently exposes contract helpers only.  Additional cross-layer helpers
should be added here to keep a stable public surface.
"""

from .contracts import load_current as load_contract  # re-export

__all__ = [
    "load_contract",
] 