"""Information Architecture (IA) APIs: orgs, collections, shares, revisions, favorites/recents.

Zero-setup, Redis-backed (with in-memory fallback) storage for launch. Postgres
can be added later without changing call-sites.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from ice_api.dependencies import rate_limit
from ice_api.redis_client import get_redis
from ice_api.security import get_request_identity, require_auth

from .blueprints import _load_blueprint as _load_blueprint_by_id  # type: ignore

router = APIRouter(prefix="/api/v1", tags=["ia"])  # Mounted in main.py


# ------------------------------- Models -------------------------------------


class Org(BaseModel):
    """Organization tenant record.

    Args:
        id (str): Organization identifier.
        name (str): Human-friendly name.
    """

    id: str
    name: str


class Collection(BaseModel):
    """Collection groups items (workflows) inside a project.

    Args:
        id (str): Collection id.
        project_id (str): Project owner id.
        name (str): Human name.
        parent_id (str | None): Optional parent collection id (tree).
        tags (list[str]): Optional tags.
    """

    id: str
    project_id: str
    name: str
    parent_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ShareGrant(BaseModel):
    """Share configuration for an item or collection."""

    subject_id: str
    role: str  # viewer | editor | owner


class RevisionMeta(BaseModel):
    """Immutable revision metadata for a workflow."""

    revision_id: str
    workflow_id: str
    created_at: int


class FavoritesList(BaseModel):
    items: List[str]


# ------------------------------- Helpers ------------------------------------


def _org_key(org_id: str) -> str:
    return f"org:{org_id}"


def _col_key(col_id: str) -> str:
    return f"col:{col_id}"


def _col_items_key(col_id: str) -> str:
    return f"colitems:{col_id}"


def _share_key(resource: str, res_id: str) -> str:
    return f"share:{resource}:{res_id}"


def _rev_index_key(workflow_id: str) -> str:
    return f"revindex:{workflow_id}"


def _rev_blob_key(workflow_id: str, rev_id: str) -> str:
    return f"rev:{workflow_id}:{rev_id}"


def _fav_key(user_id: str) -> str:
    return f"fav:{user_id}"


async def _save_json(key: str, value: BaseModel, request: Request) -> None:
    try:
        redis = get_redis()
        await redis.set(key, value.model_dump_json())  # type: ignore[misc]
        return
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    store[key] = value.model_dump(mode="json")
    request.app.state._kv = store  # type: ignore[attr-defined]


async def _load_json(model: type[BaseModel], key: str, request: Request) -> BaseModel:
    try:
        redis = get_redis()
        raw = await redis.get(key)  # type: ignore[misc]
        if raw:
            return model.model_validate_json(raw)
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    if key not in store:
        raise KeyError(key)
    return model.model_validate(store[key])


# ------------------------------- Routes: Orgs --------------------------------


@router.post(
    "/orgs",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=Org,
)
async def create_org(request: Request, payload: Org = Body(...)) -> Org:  # noqa: D401
    await _save_json(_org_key(payload.id), payload, request)
    return payload


@router.get(
    "/orgs",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=List[Org],
)
async def list_orgs(request: Request) -> List[Org]:  # noqa: D401
    # Simple scan in both redis and in-memory
    out: List[Org] = []
    try:
        redis = get_redis()
        async for k in redis.scan_iter("org:*"):
            raw = await redis.get(k)  # type: ignore[misc]
            if raw:
                out.append(Org.model_validate_json(raw))
        if out:
            return out
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    for k, v in store.items():
        if isinstance(k, str) and k.startswith("org:"):
            out.append(Org.model_validate(v))
    return out


# --------------------------- Routes: Collections -----------------------------


@router.post(
    "/projects/{project_id}/collections",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=Collection,
)
async def create_collection(  # noqa: D401
    request: Request, project_id: str, payload: Collection = Body(...)
) -> Collection:
    if payload.project_id != project_id:
        raise HTTPException(status_code=400, detail="project_id mismatch")
    await _save_json(_col_key(payload.id), payload, request)
    return payload


@router.get(
    "/projects/{project_id}/collections",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=List[Collection],
)
async def list_collections(request: Request, project_id: str) -> List[Collection]:  # noqa: D401
    out: List[Collection] = []
    try:
        redis = get_redis()
        async for k in redis.scan_iter("col:*"):
            raw = await redis.get(k)  # type: ignore[misc]
            if raw:
                c = Collection.model_validate_json(raw)
                if c.project_id == project_id:
                    out.append(c)
        if out:
            return out
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    for k, v in store.items():
        if isinstance(k, str) and k.startswith("col:"):
            c = Collection.model_validate(v)
            if c.project_id == project_id:
                out.append(c)
    return out


class AddItem(BaseModel):
    workflow_id: str


@router.post(
    "/collections/{collection_id}/items",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def add_item_to_collection(  # noqa: D401
    request: Request, collection_id: str, payload: AddItem = Body(...)
) -> Response:
    try:
        await _load_json(Collection, _col_key(collection_id), request)
    except Exception:
        raise HTTPException(status_code=404, detail="collection not found")
    try:
        redis = get_redis()
        await redis.sadd(_col_items_key(collection_id), payload.workflow_id)  # type: ignore[misc]
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    key = _col_items_key(collection_id)
    current = set(store.get(key, [])) if isinstance(store.get(key), list) else set()
    current.add(payload.workflow_id)
    store[key] = list(current)
    request.app.state._kv = store  # type: ignore[attr-defined]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/collections/{collection_id}/items",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=List[str],
)
async def list_collection_items(request: Request, collection_id: str) -> List[str]:  # noqa: D401
    try:
        redis = get_redis()
        vals = await redis.smembers(_col_items_key(collection_id))  # type: ignore[misc]
        out: List[str] = []
        for v in vals:
            out.append(v.decode() if isinstance(v, (bytes, bytearray)) else str(v))
        return out
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    key = _col_items_key(collection_id)
    if isinstance(store.get(key), list):
        return [str(x) for x in store.get(key, [])]
    return []


# --------------------------- Routes: Revisions -------------------------------


class CreateRevisionRequest(BaseModel):
    note: Optional[str] = None


@router.post(
    "/workflows/{workflow_id}/revisions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=RevisionMeta,
)
async def create_revision(  # noqa: D401
    request: Request, workflow_id: str, payload: CreateRevisionRequest = Body(None)
) -> RevisionMeta:
    bp = await _load_blueprint_by_id(workflow_id)
    # Create a deterministic short revision id from workflow payload and note
    rev_basis = (workflow_id, bp.model_dump_json(), (payload.note or ""))
    rev_id = f"r{abs(hash(rev_basis)) % (10**12)}"
    import time as _time

    created = int(_time.time())
    meta = RevisionMeta(revision_id=rev_id, workflow_id=workflow_id, created_at=created)
    # Save blob
    try:
        redis = get_redis()
        await redis.set(_rev_blob_key(workflow_id, rev_id), bp.model_dump_json())  # type: ignore[misc]
        await redis.lpush(_rev_index_key(workflow_id), rev_id)  # type: ignore[misc]
    except Exception:
        # In-memory fallback
        store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
        store[_rev_blob_key(workflow_id, rev_id)] = bp.model_dump(mode="json")
        idx = store.get(_rev_index_key(workflow_id), [])
        if not isinstance(idx, list):
            idx = []
        store[_rev_index_key(workflow_id)] = [rev_id] + idx
        request.app.state._kv = store  # type: ignore[attr-defined]
    return meta


@router.get(
    "/workflows/{workflow_id}/revisions",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=List[RevisionMeta],
)
async def list_revisions(request: Request, workflow_id: str) -> List[RevisionMeta]:  # noqa: D401
    out: List[RevisionMeta] = []
    try:
        redis = get_redis()
        rev_ids = await redis.lrange(_rev_index_key(workflow_id), 0, -1)  # type: ignore[misc]
        import time as _time

        now = int(_time.time())
        for rid in rev_ids:
            rid_str = rid.decode() if isinstance(rid, (bytes, bytearray)) else str(rid)
            out.append(
                RevisionMeta(
                    revision_id=rid_str, workflow_id=workflow_id, created_at=now
                )
            )
        return out
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    ids = store.get(_rev_index_key(workflow_id), [])
    if isinstance(ids, list):
        import time as _time

        now = int(_time.time())
        return [
            RevisionMeta(revision_id=str(r), workflow_id=workflow_id, created_at=now)
            for r in ids
        ]
    return []


# --------------------------- Routes: Favorites/Recents -----------------------


@router.post(
    "/workflows/{workflow_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def add_favorite(request: Request, workflow_id: str) -> Response:  # noqa: D401
    org_id, user_id = get_request_identity(request)
    uid = user_id or "anon"
    try:
        redis = get_redis()
        await redis.sadd(_fav_key(uid), workflow_id)  # type: ignore[misc]
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    key = _fav_key(uid)
    favs = set(store.get(key, [])) if isinstance(store.get(key), list) else set()
    favs.add(workflow_id)
    store[key] = list(favs)
    request.app.state._kv = store  # type: ignore[attr-defined]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/favorites",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=FavoritesList,
)
async def list_favorites(request: Request) -> FavoritesList:  # noqa: D401
    org_id, user_id = get_request_identity(request)
    uid = user_id or "anon"
    try:
        redis = get_redis()
        vals = await redis.smembers(_fav_key(uid))  # type: ignore[misc]
        out: List[str] = []
        for v in vals:
            out.append(v.decode() if isinstance(v, (bytes, bytearray)) else str(v))
        return FavoritesList(items=out)
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    key = _fav_key(uid)
    if isinstance(store.get(key), list):
        return FavoritesList(items=[str(x) for x in store.get(key, [])])
    return FavoritesList(items=[])
