"""Blueprint management REST endpoints."""

from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Request, status
from pydantic import ValidationError

from ice_core.models.mcp import Blueprint

router = APIRouter(prefix="/api/v1/blueprints", tags=["blueprints"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_store(request: Request) -> Dict[str, Blueprint]:  # noqa: D401 – helper
    """Return the in-memory blueprint store living on app.state."""
    if not hasattr(request.app.state, "blueprints"):
        # Initialise lazily – should already be set up in lifespan, but stay safe
        request.app.state.blueprints = {}
    return request.app.state.blueprints  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_blueprint(  # noqa: D401 – API route
    request: Request,
    payload: Dict[str, Any] = Body(..., description="Blueprint JSON payload"),
) -> Dict[str, str]:
    """Validate and store a Blueprint.

    Returns a generated UUID so clients can reference the blueprint later.
    """

    try:
        blueprint = Blueprint.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    store = _get_store(request)

    # Simple UUID4 for now – could be hash of canonical JSON later
    blueprint_id = str(uuid.uuid4())
    store[blueprint_id] = blueprint

    return {"id": blueprint_id}
