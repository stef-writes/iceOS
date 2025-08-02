"""Expose Prometheus metrics via /metrics endpoint."""

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi import APIRouter, Response

from ice_core.metrics import EXEC_STARTED, EXEC_COMPLETED  # ensure counters imported so they register

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics_endpoint() -> Response:  # noqa: D401
    """Return Prometheus metrics in text format."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)