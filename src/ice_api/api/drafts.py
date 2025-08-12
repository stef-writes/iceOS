"""Draft management API – author-time blueprint state."""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, constr

from ice_api.security import require_auth
from ice_core.metrics import DRAFT_MUTATION_TOTAL
from ice_core.models.draft import DraftState, InMemoryDraftStore, RedisDraftStore

router = APIRouter(
    prefix="/api/v1/drafts",
    tags=["drafts"],
    dependencies=[Depends(require_auth)],
)

# ────────────────────────────────────────────────────────────
# Draft persistence store
# ────────────────────────────────────────────────────────────
from ice_core.models.draft import DraftStore


def _init_store() -> DraftStore:
    if os.getenv("USE_INMEMORY_DRAFTSTORE", "0") == "1":
        return InMemoryDraftStore()
    try:
        return RedisDraftStore()
    except RuntimeError:
        return InMemoryDraftStore()


_store: DraftStore = _init_store()

# ────────────────────────────────────────────────────────────
# Very light weight in-process rate limiter (token, route) 5 req / 10 sec
# Not suitable for production but avoids abuse in dev profile.
# ────────────────────────────────────────────────────────────
_RATE_LIMIT: Dict[Tuple[str, str], list[float]] = {}
_RATE_WINDOW = 10.0
_RATE_MAX = 5


def rate_limit(request: Request, token: str = Depends(require_auth)) -> None:  # noqa: D401
    key = (token, request.url.path)
    now = time.time()
    bucket = _RATE_LIMIT.setdefault(key, [])
    # Purge old timestamps
    _RATE_LIMIT[key] = [t for t in bucket if now - t < _RATE_WINDOW]
    if len(_RATE_LIMIT[key]) >= _RATE_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _RATE_LIMIT[key].append(now)


# ────────────────────────────────────────────────────────────
# Request models
# ────────────────────────────────────────────────────────────


class LockRequest(BaseModel):
    node_id: constr(min_length=1, max_length=64)  # type: ignore


class PositionRequest(BaseModel):
    node_id: constr(min_length=1, max_length=64)  # type: ignore
    x: int = Field(..., ge=0, le=5000)
    y: int = Field(..., ge=0, le=5000)


class InstantiateRequest(BaseModel):
    node_id: constr(min_length=1, max_length=64)  # type: ignore
    node_type: str = Field(...)
    extra: Dict[str, Any] | None = None


# ────────────────────────────────────────────────────────────
# Helper serialization
# ────────────────────────────────────────────────────────────


def _as_json(state: DraftState) -> Dict[str, Any]:
    return {
        "prompt_history": state.prompt_history,
        "mermaid_versions": state.mermaid_versions,
        "locked_nodes": state.locked_nodes,
        "node_positions": state.node_positions,
        "meta": state.meta,
        "blueprint": (
            state.last_blueprint.model_dump(mode="json")
            if state.last_blueprint
            else None
        ),
    }


async def _get_state(session_id: str) -> DraftState:
    state = await _store.load(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return state


async def _save_and_broadcast(
    session_id: str, state: DraftState, action: str
) -> Dict[str, Any]:
    from ice_api.ws import draft_ws as _draft_ws

    await _store.save(session_id, state)
    DRAFT_MUTATION_TOTAL.labels(action=action).inc()
    await _draft_ws.broadcast(session_id, state)
    return _as_json(state)


def _calculate_version_lock(state: DraftState) -> str:
    """Return SHA-256 hash of draft state (excluding existing version lock)."""
    meta_copy = dict(state.meta)
    meta_copy.pop("version_lock", None)
    payload = {
        "prompt_history": state.prompt_history,
        "mermaid_versions": state.mermaid_versions,
        "locked_nodes": state.locked_nodes,
        "node_positions": state.node_positions,
        "nodes": state.nodes,
        "meta": meta_copy,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


# Helper – optimistic-locking check for mutating routes


def _require_match_version(request: Request, state: DraftState) -> None:  # noqa: D401
    client_lock = request.headers.get("X-Version-Lock")
    if client_lock is None:
        raise HTTPException(status_code=428, detail="Missing X-Version-Lock header")

    server_lock = _calculate_version_lock(state)
    if client_lock != server_lock:
        raise HTTPException(status_code=409, detail="Draft version conflict")


# ────────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────────


@router.post("/{session_id}", response_model=Dict[str, Any])
async def create_or_get_draft(
    session_id: str, _: None = Depends(rate_limit)
) -> Dict[str, Any]:  # noqa: D401
    """Ensure a draft exists for session and return its state.

    If no draft exists, a new empty DraftState is created and persisted.
    """
    state = await _store.load(session_id)
    if state is None:
        state = DraftState()
        await _store.save(session_id, state)
    return _as_json(state)


@router.get("/{session_id}", response_model=Dict[str, Any])
async def get_draft(session_id: str, _: None = Depends(rate_limit)) -> Dict[str, Any]:  # noqa: D401
    state = await _get_state(session_id)
    return _as_json(state)


@router.post("/{session_id}/lock", response_model=Dict[str, Any])
async def lock_node(
    session_id: str, req: LockRequest, _: None = Depends(rate_limit)
) -> Dict[str, Any]:
    state = await _get_state(session_id)
    if req.node_id not in state.locked_nodes:
        state.locked_nodes.append(req.node_id)
    state.meta.setdefault("status", {})[req.node_id] = "locked"
    return await _save_and_broadcast(session_id, state, "lock")


@router.post("/{session_id}/position", response_model=Dict[str, Any])
async def update_position(
    session_id: str, req: PositionRequest, _: None = Depends(rate_limit)
) -> Dict[str, Any]:
    state = await _get_state(session_id)
    state.node_positions[req.node_id] = (req.x, req.y)
    return await _save_and_broadcast(session_id, state, "position")


@router.post("/{session_id}/instantiate", response_model=Dict[str, Any])
async def instantiate_node(
    session_id: str, req: InstantiateRequest, _: None = Depends(rate_limit)
) -> Dict[str, Any]:
    state = await _get_state(session_id)
    state.meta.setdefault("status", {})[req.node_id] = "real"
    # Bump semantic version stored in meta
    version = int(state.meta.get("schema_rev", 0)) + 1
    state.meta["schema_rev"] = version
    return await _save_and_broadcast(session_id, state, "instantiate")
