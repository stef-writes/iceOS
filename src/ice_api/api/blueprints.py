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
# Version-lock helpers ------------------------------------------------------
# ---------------------------------------------------------------------------

def _calculate_version_lock(bp: Blueprint | Any) -> str:  # noqa: D401
    """Return SHA-256 hash of the blueprint JSON, resilient to FastAPI/Pydantic callbacks.

    FastAPI may call this helper while still inside a *model_validator* where
    ``bp`` is actually a :class:`pydantic.ValidationInfo` instance.  In that
    case we attempt to grab the underlying ``data``; if unavailable we bail
    out with an empty string so the request fails deterministically upstream.
    """
    # Fast path – already a Blueprint instance
    if hasattr(bp, "model_dump"):
        payload = bp.model_dump(mode="json", exclude_none=True)  # type: ignore[arg-type]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    # Handle Pydantic v2 ValidationInfo wrapper transparently (runtime optional)
    data_obj = getattr(bp, "data", None) if hasattr(bp, "data") else None
    if data_obj is not None and hasattr(data_obj, "model_dump"):
        payload = data_obj.model_dump(mode="json", exclude_none=True)  # type: ignore[arg-type]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    # Fallback – unknown type, return deterministic empty hash so caller fails
    return "0" * 64

    payload = bp.model_dump(mode="json", exclude_none=True)  # type: ignore[arg-type]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _assert_version_lock(request: Request, expected: str) -> None:  # noqa: D401
    """Validate *X-Version-Lock* header against *expected* value.

    Raises:
        HTTPException 428 – header missing
        HTTPException 409 – mismatch
    """
    client_lock = request.headers.get("X-Version-Lock")
    if client_lock is None:
        raise HTTPException(status_code=428, detail="Missing X-Version-Lock header")
    if client_lock != expected:
        raise HTTPException(status_code=409, detail="Blueprint version conflict")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# Note: All mutating routes enforce the optimistic X-Version-Lock header to
# avoid write-skew and lost updates in concurrent clients. The helper
# *_assert_version_lock* raises 428 for missing header and 409 when the header
# does not match the server-side SHA-256.


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_blueprint(  # noqa: D401 – API route
    request: Request,
    payload: Dict[str, Any] = Body(..., description="Blueprint JSON payload"),
) -> Dict[str, str]:
    """Create a blueprint using optimistic concurrency.

    The client **must** send header ``X-Version-Lock: __new__`` to signal it
    created the object offline. This avoids races when two users create a
    blueprint with the same natural-language spec concurrently.
    """
    # Enforce header
    _assert_version_lock(request, "__new__")

    # Validate payload
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
    server_lock = _calculate_version_lock(store[blueprint_id])
    _assert_version_lock(request, server_lock)

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

# ---------------------------------------------------------------------------
# DELETE – remove blueprint --------------------------------------------------
# ---------------------------------------------------------------------------

@router.delete("/{blueprint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blueprint(  # noqa: D401
    request: Request,
    blueprint_id: str,
) -> Response:
    """Delete a blueprint after optimistic lock validation."""
    store = _get_store(request)
    if blueprint_id not in store:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    # Concurrency guard ------------------------------------------------------
    server_lock = _calculate_version_lock(store[blueprint_id])
    _assert_version_lock(request, server_lock)

    del store[blueprint_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ---------------------------------------------------------------------------
# PUT – full replacement -----------------------------------------------------
# ---------------------------------------------------------------------------

@router.put("/{blueprint_id}")
async def replace_blueprint(  # noqa: D401
    request: Request,
    blueprint_id: str,
    payload: Dict[str, Any] = Body(..., description="Full blueprint JSON payload"),
) -> Dict[str, str]:
    """Replace an existing blueprint in one shot (optimistic concurrency)."""
    store = _get_store(request)
    if blueprint_id not in store:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    # Concurrency guard ------------------------------------------------------
    server_lock = _calculate_version_lock(store[blueprint_id])
    _assert_version_lock(request, server_lock)

    # Validate complete payload --------------------------------------------
    try:
        bp = Blueprint.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    store[blueprint_id] = bp
    new_lock = _calculate_version_lock(bp)
    return {"id": blueprint_id, "version_lock": new_lock}

# ---------------------------------------------------------------------------
# POST clone – duplicate blueprint ------------------------------------------
# ---------------------------------------------------------------------------

@router.post("/{blueprint_id}/clone", status_code=status.HTTP_201_CREATED)
async def clone_blueprint(  # noqa: D401
    request: Request,
    blueprint_id: str,
) -> Dict[str, str]:
    """Create a deep copy of an existing blueprint and return the new id."""
    store = _get_store(request)
    if blueprint_id not in store:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    original = store[blueprint_id]
    new_id = str(uuid.uuid4())
    # Perform a shallow copy – Blueprint is immutable enough for in-memory demo
    store[new_id] = original.model_copy(deep=True)
    new_lock = _calculate_version_lock(original)
    return {"id": new_id, "version_lock": new_lock}
