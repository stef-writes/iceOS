"""
API package for iceOS
"""

from ice_api.api.mcp import router as mcp_router

__all__ = [
    "mcp_router",
]
