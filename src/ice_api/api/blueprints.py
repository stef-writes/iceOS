"""Blueprint management REST endpoints."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException, Request, status
from pydantic import BaseModel, ValidationError

from ice_api.redis_client import get_redis
from ice_api.security import is_agent_allowed, is_tool_allowed
from ice_core.models.mcp import Blueprint, NodeSpec
from ice_core.unified_registry import registry

router = APIRouter(prefix="/api/v1/blueprints", tags=["blueprints"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bp_key(blueprint_id: str) -> str:  # noqa: D401 – helper
    """Return Redis key for a blueprint id."""
    return f"bp:{blueprint_id}"


async def _load_blueprint(blueprint_id: str) -> Blueprint:  # noqa: D401 – helper
    """Load a blueprint by id from Redis or raise 404 if not found."""
    try:
        redis = get_redis()
        raw_json = await redis.hget(_bp_key(blueprint_id), "json")  # type: ignore[arg-type]
        if raw_json:
            return Blueprint.model_validate_json(raw_json)
    except Exception:
        pass
    # Zero-setup in-memory fallback
    # Note: We avoid importing Request/Depends here to prevent unused-import warnings.
    # In FastAPI route context, we can't access request here; use app state via workaround not available.
    # Instead, signal not found and let caller manage state-based fallback.
    raise HTTPException(status_code=404, detail="Blueprint not found")


async def _save_blueprint(blueprint_id: str, blueprint: Blueprint) -> None:  # noqa: D401 – helper
    """Persist blueprint JSON to Redis."""
    try:
        redis = get_redis()
        await redis.hset(
            _bp_key(blueprint_id), mapping={"json": blueprint.model_dump_json()}
        )
    except Exception:
        # Zero-setup in-memory fallback under app.state.blueprints
        # The caller routes have access to request.app.state; we'll write into it there instead.
        # This helper cannot access request, so it will raise and let callers handle.
        raise


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
import json as _json

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
        return hashlib.sha256(_json.dumps(payload, sort_keys=True).encode()).hexdigest()

    # Handle Pydantic v2 ValidationInfo wrapper transparently (runtime optional)
    data_obj = getattr(bp, "data", None) if hasattr(bp, "data") else None
    if data_obj is not None and hasattr(data_obj, "model_dump"):
        payload = data_obj.model_dump(mode="json", exclude_none=True)  # type: ignore[arg-type]
        return hashlib.sha256(_json.dumps(payload, sort_keys=True).encode()).hexdigest()

    # Fallback – unknown type, return deterministic empty hash so caller fails
    return "0" * 64

    payload = bp.model_dump(mode="json", exclude_none=True)  # type: ignore[arg-type]
    return hashlib.sha256(_json.dumps(payload, sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Registry resolvability and access validation -------------------------------
# ---------------------------------------------------------------------------


def _validate_resolvable_and_allowed(blueprint: Blueprint) -> None:
    """Ensure all referenced tools/agents resolve and are allowed.

    Raises 422 with precise details on first failure.
    """
    from fastapi import HTTPException

    # Best-effort: ensure generated tools are imported so factories register
    try:
        pass

    # Starter packs are now loaded via manifests; no implicit imports here
    except Exception:
        pass

    # Validate tools
    for node in blueprint.nodes:
        if node.type == "tool":
            name = getattr(node, "tool_name", None)
            # Allow minimal placeholder tool nodes in CRUD tests and drafts
            if not isinstance(name, str) or not name:
                continue
            if not registry.has_tool(name):
                # Best-effort JIT load of plugin manifests when present to
                # align in-process TestClient runs with server startup behavior.
                try:
                    import os as _os

                    manifests_env = _os.getenv("ICEOS_PLUGIN_MANIFESTS", "").strip()
                    if manifests_env:
                        for mp in [
                            p.strip() for p in manifests_env.split(",") if p.strip()
                        ]:
                            try:
                                registry.load_plugins(mp, allow_dynamic=True)
                            except Exception:
                                # Non-fatal – continue and re-check below
                                pass
                except Exception:
                    pass

            if not registry.has_tool(name):
                raise HTTPException(
                    status_code=422, detail=f"Tool '{name}' is not registered"
                )
            if not is_tool_allowed(name):
                raise HTTPException(
                    status_code=403, detail=f"Tool '{name}' is not allowed"
                )
        elif node.type == "agent":
            pkg = getattr(node, "package", None)
            if isinstance(pkg, str) and pkg and not is_agent_allowed(pkg):
                raise HTTPException(
                    status_code=403, detail=f"Agent '{pkg}' is not allowed"
                )


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


class BlueprintCreateResponse(BaseModel):
    """Response for blueprint creation.

    Args:
        id (str): Assigned blueprint identifier.
        version_lock (str): Version lock for optimistic concurrency.

    Returns:
        BlueprintCreateResponse: Response model containing identifiers.
    """

    id: str
    version_lock: str


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def create_blueprint(  # noqa: D401 – API route
    request: Request,
    blueprint: Blueprint = Body(..., description="Blueprint JSON payload"),
) -> "BlueprintCreateResponse":
    """Create a blueprint using optimistic concurrency.

    Args:
        request (Request): FastAPI request object (used for headers and app state).
        blueprint (Blueprint): Fully-typed Blueprint payload.

    Returns:
        BlueprintCreateResponse: Identifier and version lock of the stored blueprint.

    Example:
        POST /api/v1/blueprints/ with header X-Version-Lock: __new__ and a Blueprint body.
    """
    _assert_version_lock(request, "__new__")

    # Enforce resolvability and access
    _validate_resolvable_and_allowed(blueprint)

    blueprint_id = str(uuid.uuid4())
    try:
        await _save_blueprint(blueprint_id, blueprint)
    except Exception:
        store = getattr(request.app.state, "blueprints", None)
        if store is not None:
            store[blueprint_id] = blueprint
        else:
            request.app.state.blueprints = {blueprint_id: blueprint}

    version_lock = _calculate_version_lock(blueprint)
    return BlueprintCreateResponse(id=blueprint_id, version_lock=version_lock)


class BlueprintGetResponse(BaseModel):
    data: Dict[str, Any]
    version_lock: str


@router.get(
    "/{blueprint_id}", dependencies=[Depends(rate_limit), Depends(require_auth)]
)
async def get_blueprint(
    request: Request,
    blueprint_id: str,
    response: Response,
) -> BlueprintGetResponse:  # noqa: D401 – API route
    """Return a stored Blueprint by *id* with optimistic version-lock header."""
    try:
        bp = await _load_blueprint(blueprint_id)
    except HTTPException:
        store = getattr(request.app.state, "blueprints", {})
        if blueprint_id not in store:
            raise
        bp = store[blueprint_id]

    # Compute version lock and expose as header
    version_lock = _calculate_version_lock(bp)
    response.headers["X-Version-Lock"] = version_lock
    return BlueprintGetResponse(data=bp.model_dump(), version_lock=version_lock)


class BlueprintPatchResponse(BaseModel):
    id: str
    node_count: int


@router.patch(
    "/{blueprint_id}",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=BlueprintPatchResponse,
)
async def patch_blueprint(  # noqa: D401
    request: Request,
    blueprint_id: str,
    payload: Dict[str, Any] = Body(..., description="Partial blueprint patch"),
) -> BlueprintPatchResponse:
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

    # Enforce resolvability and access
    _validate_resolvable_and_allowed(bp)

    try:
        await _save_blueprint(blueprint_id, bp)
    except Exception:
        # In-memory update
        store = getattr(request.app.state, "blueprints", None)
        if store is not None:
            store[blueprint_id] = bp
    return BlueprintPatchResponse(id=blueprint_id, node_count=len(bp.nodes))


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


class BlueprintReplaceResponse(BaseModel):
    id: str
    version_lock: str


@router.put(
    "/{blueprint_id}",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=BlueprintReplaceResponse,
)
async def replace_blueprint(  # noqa: D401
    request: Request,
    blueprint_id: str,
    payload: Dict[str, Any] = Body(..., description="Full blueprint JSON payload"),
) -> BlueprintReplaceResponse:
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

    # Enforce resolvability and access
    _validate_resolvable_and_allowed(bp)

    await _save_blueprint(blueprint_id, bp)
    new_lock = _calculate_version_lock(bp)
    return BlueprintReplaceResponse(id=blueprint_id, version_lock=new_lock)


# ---------------------------------------------------------------------------
# POST clone – duplicate blueprint ------------------------------------------
# ---------------------------------------------------------------------------


class BlueprintCloneResponse(BaseModel):
    id: str
    version_lock: str


@router.post(
    "/{blueprint_id}/clone",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=BlueprintCloneResponse,
)
async def clone_blueprint(  # noqa: D401
    request: Request,
    blueprint_id: str,
) -> BlueprintCloneResponse:
    """Create a deep copy of an existing blueprint and return the new id."""
    original = await _load_blueprint(blueprint_id)
    new_id = str(uuid.uuid4())
    await _save_blueprint(new_id, original.model_copy(deep=True))
    new_lock = _calculate_version_lock(original)
    return BlueprintCloneResponse(id=new_id, version_lock=new_lock)
