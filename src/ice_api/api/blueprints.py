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

import hashlib
import json

# ---------------------------------------------------------------------------
# Version-lock helper -------------------------------------------------------
# ---------------------------------------------------------------------------

def _calculate_version_lock(bp: Blueprint) -> str:  # noqa: D401
    """Return SHA-256 hash of the blueprint's JSON representation."""
    payload = bp.model_dump(mode="json", exclude_none=True)
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

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

    version_lock = _calculate_version_lock(blueprint)
    return {"id": blueprint_id, "version_lock": version_lock}


from fastapi import Depends, Response
from ice_api.dependencies import rate_limit
from ice_api.security import require_auth


@router.get("/{blueprint_id}", dependencies=[Depends(rate_limit), Depends(require_auth)])
async def get_blueprint(
    request: Request,
    blueprint_id: str,
    response: Response,
) -> Dict[str, Any]:  # noqa: D401 – API route
    """Return a stored Blueprint by *id* with optimistic version-lock header."""
    store = _get_store(request)
    bp = store.get(blueprint_id)
    if bp is None:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    # Compute version lock and expose as header
    version_lock = _calculate_version_lock(bp)
    response.headers["X-Version-Lock"] = version_lock
    return bp.model_dump()


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

    # Optimistic locking --------------------------------------------------
    client_lock = request.headers.get("X-Version-Lock")
    if client_lock is None:
        raise HTTPException(status_code=428, detail="Missing X-Version-Lock header")

    server_lock = _calculate_version_lock(store[blueprint_id])
    if client_lock != server_lock:
        raise HTTPException(status_code=409, detail="Blueprint version conflict")

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
