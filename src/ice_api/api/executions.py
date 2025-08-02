"""Execution management REST endpoints."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Request, status

from ice_core.models.mcp import Blueprint
from ice_core.services import ServiceLocator

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


from typing import TypedDict, cast

class _ExecutionRecord(TypedDict, total=False):
    status: str
    blueprint_id: str
    result: Any
    error: str
    _event: asyncio.Event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_exec_store(request: Request) -> Dict[str, _ExecutionRecord]:  # noqa: D401
    if not hasattr(request.app.state, "executions"):
        request.app.state.executions = {}
    return cast(Dict[str, _ExecutionRecord], request.app.state.executions)  # type: ignore[attr-defined]


def _get_blueprint(request: Request, blueprint_id: str) -> Blueprint:
    store = getattr(request.app.state, "blueprints", None)
    if store is None or blueprint_id not in store:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return cast(Blueprint, store[blueprint_id])


async def _run_workflow_async(execution_id: str, bp: Blueprint, inputs: Optional[Dict[str, Any]], store: Dict[str, _ExecutionRecord]) -> None:
    """Background task that executes the workflow and updates *store*."""
    service = ServiceLocator.get("workflow_execution_service")
    record = store[execution_id]
    try:
        record["status"] = "running"
        record["_event"].set()
        result = await service.execute_blueprint(bp.nodes, inputs=inputs, name=f"run_{execution_id}")  # type: ignore[arg-type]
        record["status"] = "completed"
        record["result"] = result.model_dump() if hasattr(result, "model_dump") else result  # type: ignore[assignment]
        record["_event"].set()
    except Exception as exc:  # noqa: BLE001
        record["status"] = "failed"
        record["error"] = str(exc)
        record["_event"].set()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def start_execution(  # noqa: D401 – API route
    request: Request,
    payload: Dict[str, Any] = Body(..., embed=True),
) -> Dict[str, str]:
    """Kick off a workflow execution.

    Expected JSON body::
        {
            "blueprint_id": "...",            # required
            "inputs": {...}                     # optional initial inputs
        }
    """

    blueprint_id: str | None = payload.get("blueprint_id")
    if not blueprint_id:
        raise HTTPException(status_code=422, detail="blueprint_id is required")

    inputs = payload.get("inputs")

    blueprint = _get_blueprint(request, blueprint_id)

    exec_store = _get_exec_store(request)
    execution_id = str(uuid.uuid4())

    exec_store[execution_id] = cast(_ExecutionRecord, {
        "status": "pending",
        "blueprint_id": blueprint_id,
        "_event": asyncio.Event(),  # internal notification hook
    })

    # Run in background – FastAPI will await task completion if lifespan ends
    asyncio.create_task(_run_workflow_async(execution_id, blueprint, inputs, exec_store))

    return {"execution_id": execution_id}


@router.get("/{execution_id}")
async def get_execution_status(request: Request, execution_id: str) -> Dict[str, Any]:  # noqa: D401
    store = _get_exec_store(request)
    if execution_id not in store:
        raise HTTPException(status_code=404, detail="Execution not found")
    record = store[execution_id]
    return {k: v for k, v in record.items() if not k.startswith("_") }
