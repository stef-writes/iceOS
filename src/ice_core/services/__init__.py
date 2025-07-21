"""Service interfaces for *ice_core*.

Exposes contract helpers only – other utilities now live in upper layers.
"""

from .contracts import load_current as load_contract  # re-export

__all__ = [
    "load_contract",
]
