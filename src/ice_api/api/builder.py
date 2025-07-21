"""Deprecated builder API placeholder.

This module exists solely to satisfy legacy imports (`ice_api.api.builder`).
All real builder operations have moved elsewhere; the router is empty.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/builder", tags=["builder"])

# Intentionally left empty – the endpoints were removed in the refactor.
