"""Blueprint management REST endpoints."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, cast

from fastapi import APIRouter, Body, HTTPException, Request, status
from pydantic import ValidationError

from ice_core.models.mcp import Blueprint, NodeSpec

router = APIRouter(prefix="/api/v1/blueprints", tags=["blueprints"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_store(request: Request) -> Dict[str, Blueprint]:  # noqa: D401 – helper
    """Return the in-memory blueprint store living on app.state."""
    if not hasattr(request.app.state, "blueprints"):
        request.app.state.blueprints = {}
    return cast(Dict[str, Blueprint], request.app.state.blueprints)  # type: ignore[attr-defined]


def _merge_nodes(existing: List[NodeSpec], patch_nodes: List[NodeSpec]) -> List[NodeSpec]:
    """Merge *patch_nodes* into *existing* by node id (add/update/remove)."""
    mapping = {n.id: n for n in existing}
    for p in patch_nodes:
        if p.type == "__delete__":
            mapping.pop(p.id, None)
        else:
            mapping[p.id] = p
    return list(mapping.values())

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_blueprint(  # noqa: D401 – API route
    request: Request,
    payload: Dict[str, Any] = Body(..., description="Blueprint JSON payload"),
) -> Dict[str, str]:
    """Validate and store a Blueprint. Returns its generated id."""
    try:
        blueprint = Blueprint.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    blueprint_id = str(uuid.uuid4())
    _get_store(request)[blueprint_id] = blueprint
    return {"id": blueprint_id}


@router.patch("/{blueprint_id}")
async def patch_blueprint(  # noqa: D401
    request: Request,
    blueprint_id: str,
    payload: Dict[str, Any] = Body(..., description="Partial blueprint patch"),
) -> Dict[str, Any]:
    """Incrementally update a stored blueprint.

    Payload schema (minimal):
        {
          "nodes": [ { ...NodeSpec... | {"id": "node_id", "type": "__delete__"} ]
        }
    """
    store = _get_store(request)
    if blueprint_id not in store:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    bp = store[blueprint_id]

    patch_nodes_raw = payload.get("nodes", [])
    try:
        patch_nodes = [NodeSpec.model_validate(n) for n in patch_nodes_raw]
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    merged_nodes = _merge_nodes(bp.nodes, patch_nodes)
    bp.nodes = merged_nodes  # type: ignore[assignment]

    # Validate the updated blueprint
    try:
        Blueprint.model_validate(bp.model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    store[blueprint_id] = bp
    return {"id": blueprint_id, "node_count": len(bp.nodes)}
