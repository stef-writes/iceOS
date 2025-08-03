"""
API package for iceOS
"""

from ice_api.api.mcp import router as mcp_router
from ice_api.api.drafts import router as drafts_router

__all__ = [
    "mcp_router",
    "drafts_router",
]
