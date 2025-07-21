"""Workflow CRUD + execution stream endpoints.

These minimal endpoints unblock the front-end canvas while we build out a
full persistence + execution engine.  For now we keep everything strictly
in-memory and *demo-only*.

Rules honoured:
* Pure Pydantic models (`NodeModel`, `EdgeModel`, `WorkflowDefinition`).
* No cross-layer imports into core logic – we only touch the API layer and
  the public `ice_sdk.skills.registry` interface.
* All external side-effects (storage, WS broadcast) live inside this module.
* Async/await used exclusively – no blocking calls.
"""

import asyncio
import uuid
from typing import Any, AsyncIterator, Dict, List, Set

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.websockets import WebSocketState
from pydantic import BaseModel, Field

from ice_sdk.registry.skill import global_skill_registry

router = APIRouter(prefix="/v1", tags=["workflows"])

# ---------------------------------------------------------------------------
# Pydantic models ------------------------------------------------------------
# ---------------------------------------------------------------------------


class NodeModel(BaseModel):
    """Minimal node DTO for the canvas demo."""

    id: str = Field(..., description="Unique node identifier")
    type: str = Field(..., description="Node kind, e.g. 'skill', 'llm'")
    name: str = Field(..., description="Human-readable name or registry key")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Opaque config blob"
    )


class EdgeModel(BaseModel):
    """Simple directed edge between nodes."""

    source: str = Field(..., description="Upstream node id")
    target: str = Field(..., description="Downstream node id")


class WorkflowDefinition(BaseModel):
    """Collection of nodes + edges describing a DAG."""

    nodes: List[NodeModel]
    edges: List[EdgeModel]

    async def validate_for_demo(self) -> None:  # noqa: D401
        """Lightweight async validation.

        * Ensures Skill names are resolvable.
        * Delegates to each Skill's own `validate()` hook when present.
        """

        for node in self.nodes:
            if node.type == "skill":
                try:
                    skill = global_skill_registry.get(node.name)
                except Exception as exc:  # pragma: no cover – propagate clarity
                    raise ValueError(f"Unknown skill '{node.name}'") from exc

                # Optional, but keeps interface generic
                validate_fn = getattr(skill, "validate", None)
                if callable(validate_fn):
                    await asyncio.to_thread(validate_fn)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# In-memory store (demo-only, *no* persistence) ------------------------------
# ---------------------------------------------------------------------------

_WORKFLOW_STORE: Dict[str, WorkflowDefinition] = {}
_STORE_LOCK: asyncio.Lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# REST endpoints -------------------------------------------------------------
# ---------------------------------------------------------------------------


@router.post("/workflows", response_model=dict[str, str])
async def save_workflow(workflow: WorkflowDefinition) -> dict[str, str]:  # noqa: D401
    """Persist a workflow in memory and return its id."""

    await workflow.validate_for_demo()
    workflow_id = uuid.uuid4().hex
    async with _STORE_LOCK:
        _WORKFLOW_STORE[workflow_id] = workflow
    return {"id": workflow_id}


@router.get("/workflows/{workflow_id}", response_model=WorkflowDefinition)
async def get_workflow(workflow_id: str) -> WorkflowDefinition:  # noqa: D401
    """Fetch a stored workflow by id."""

    wf = _WORKFLOW_STORE.get(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


# ---------------------------------------------------------------------------
# Execution status WebSocket -------------------------------------------------
# ---------------------------------------------------------------------------

_EXECUTION_SUBSCRIBERS: Set[WebSocket] = set()


async def _demo_status_generator() -> AsyncIterator[dict[str, Any]]:  # type: ignore[name-defined]
    """Fake generator emitting node status updates every second."""

    nodes = ["load", "transform", "sum", "output"]
    idx = 0
    while True:
        yield {"node": nodes[idx % len(nodes)], "status": "running"}
        idx += 1
        await asyncio.sleep(1)


@router.websocket("/ws/execution")
async def execution_updates(ws: WebSocket) -> None:  # noqa: D401 – FastAPI handler
    """Stream real-time execution telemetry to the canvas UI.

    The initial version is stubbed with synthetic data so the front-end can
    integrate without waiting for the full executor bridge.
    """

    # Basic origin check (demo-only)
    if ws.headers.get("origin") not in {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws.accept()
    _EXECUTION_SUBSCRIBERS.add(ws)
    try:
        async for payload in _demo_status_generator():
            if ws.application_state == WebSocketState.DISCONNECTED:
                break
            await ws.send_json(payload)
    except WebSocketDisconnect:
        pass
    finally:
        _EXECUTION_SUBSCRIBERS.discard(ws)
