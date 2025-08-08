"""Blueprint management REST endpoints."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException, Request, status
from pydantic import ValidationError

from ice_api.redis_client import get_redis
from ice_core.models.mcp import Blueprint, NodeSpec

router = APIRouter(prefix="/api/v1/blueprints", tags=["blueprints"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bp_key(blueprint_id: str) -> str:  # noqa: D401 – helper
    """Return Redis key for a blueprint id."""
    return f"bp:{blueprint_id}"


async def _load_blueprint(blueprint_id: str) -> Blueprint:  # noqa: D401 – helper
    """Load a blueprint by id from Redis or raise 404 if not found."""
    redis = get_redis()
    raw_json = await redis.hget(_bp_key(blueprint_id), "json")  # type: ignore[arg-type]
    if not raw_json:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return Blueprint.model_validate_json(raw_json)


async def _save_blueprint(
    blueprint_id: str, blueprint: Blueprint
) -> None:  # noqa: D401 – helper
    """Persist blueprint JSON to Redis."""
    redis = get_redis()
    await redis.hset(
        _bp_key(blueprint_id), mapping={"json": blueprint.model_dump_json()}
    )


def _merge_nodes(
    existing: List[NodeSpec], patch_nodes: List[NodeSpec]
) -> List[NodeSpec]:
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


from fastapi import Depends, Response

from ice_api.dependencies import rate_limit
from ice_api.security import require_auth


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
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
    await _save_blueprint(blueprint_id, blueprint)

    version_lock = _calculate_version_lock(blueprint)
    return {"id": blueprint_id, "version_lock": version_lock}


@router.get(
    "/{blueprint_id}", dependencies=[Depends(rate_limit), Depends(require_auth)]
)
async def get_blueprint(
    request: Request,
    blueprint_id: str,
    response: Response,
) -> Dict[str, Any]:  # noqa: D401 – API route
    """Return a stored Blueprint by *id* with optimistic version-lock header."""
    bp = await _load_blueprint(blueprint_id)

    # Compute version lock and expose as header
    version_lock = _calculate_version_lock(bp)
    response.headers["X-Version-Lock"] = version_lock
    return bp.model_dump()


@router.patch(
    "/{blueprint_id}", dependencies=[Depends(rate_limit), Depends(require_auth)]
)
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
    bp = await _load_blueprint(blueprint_id)

    # Optimistic locking --------------------------------------------------
    server_lock = _calculate_version_lock(bp)
    _assert_version_lock(request, server_lock)

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

    await _save_blueprint(blueprint_id, bp)
    return {"id": blueprint_id, "node_count": len(bp.nodes)}


# ---------------------------------------------------------------------------
# DELETE – remove blueprint --------------------------------------------------
# ---------------------------------------------------------------------------


@router.delete(
    "/{blueprint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def delete_blueprint(  # noqa: D401
    request: Request,
    blueprint_id: str,
) -> Response:
    """Delete a blueprint after optimistic lock validation."""
    bp = await _load_blueprint(blueprint_id)

    # Concurrency guard ------------------------------------------------------
    server_lock = _calculate_version_lock(bp)
    _assert_version_lock(request, server_lock)

    # Mark as deleted by clearing JSON field
    redis = get_redis()
    await redis.hset(_bp_key(blueprint_id), mapping={"json": ""})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# PUT – full replacement -----------------------------------------------------
# ---------------------------------------------------------------------------


@router.put(
    "/{blueprint_id}", dependencies=[Depends(rate_limit), Depends(require_auth)]
)
async def replace_blueprint(  # noqa: D401
    request: Request,
    blueprint_id: str,
    payload: Dict[str, Any] = Body(..., description="Full blueprint JSON payload"),
) -> Dict[str, str]:
    """Replace an existing blueprint in one shot (optimistic concurrency)."""
    current = await _load_blueprint(blueprint_id)

    # Concurrency guard ------------------------------------------------------
    server_lock = _calculate_version_lock(current)
    _assert_version_lock(request, server_lock)

    # Validate complete payload --------------------------------------------
    try:
        bp = Blueprint.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    await _save_blueprint(blueprint_id, bp)
    new_lock = _calculate_version_lock(bp)
    return {"id": blueprint_id, "version_lock": new_lock}


# ---------------------------------------------------------------------------
# POST clone – duplicate blueprint ------------------------------------------
# ---------------------------------------------------------------------------


@router.post(
    "/{blueprint_id}/clone",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def clone_blueprint(  # noqa: D401
    request: Request,
    blueprint_id: str,
) -> Dict[str, str]:
    """Create a deep copy of an existing blueprint and return the new id."""
    original = await _load_blueprint(blueprint_id)
    new_id = str(uuid.uuid4())
    await _save_blueprint(new_id, original.model_copy(deep=True))
    new_lock = _calculate_version_lock(original)
    return {"id": new_id, "version_lock": new_lock}
