"""Expose Prometheus metrics via /metrics endpoint (optional)."""

from __future__ import annotations

from fastapi import APIRouter, Response

# Import counters so they register when Prometheus is enabled; safe no-op otherwise
from ice_core.metrics import EXEC_COMPLETED, EXEC_STARTED  # noqa: F401

try:  # Optional dependency
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest  # type: ignore

    _PROM_AVAILABLE = True
except Exception:  # pragma: no cover – optional
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"  # type: ignore
    _PROM_AVAILABLE = False

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics_endpoint() -> Response:  # noqa: D401
    """Return Prometheus metrics in text format when available.

    If Prometheus is not available, return an empty 200 response to avoid errors.
    """
    if _PROM_AVAILABLE:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)  # type: ignore[name-defined]
    return Response(b"", media_type=CONTENT_TYPE_LATEST)
