"""Expose Prometheus metrics via /metrics endpoint."""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ice_core.metrics import (  # noqa: F401  # ensure counters imported so they register
    EXEC_COMPLETED,
    EXEC_STARTED,
)

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics_endpoint() -> Response:  # noqa: D401
    """Return Prometheus metrics in text format."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)