"""Execution management REST endpoints."""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from ice_api.redis_client import get_redis
from ice_core.models.mcp import Blueprint
from ice_core.services import ServiceLocator
from ice_orchestrator.execution.workflow_events import EventType

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])
from typing import TypedDict, cast

from ice_api.dependencies import rate_limit
from ice_api.security import require_auth


class _ExecutionRecord(TypedDict, total=False):
    status: str
    blueprint_id: str
    result: Any
    error: str
    _event: asyncio.Event
    events: list[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _exec_key(execution_id: str) -> str:  # noqa: D401
    return f"exec:{execution_id}"


def _get_exec_store(request: Request) -> Dict[str, _ExecutionRecord]:  # noqa: D401
    # Keep in-memory store for in-process notifications; persist authoritative
    # state in Redis so runs survive restarts.
    if not hasattr(request.app.state, "executions"):
        request.app.state.executions = {}
    return cast(Dict[str, _ExecutionRecord], request.app.state.executions)  # type: ignore[attr-defined]


async def _get_blueprint(request: Request, blueprint_id: str) -> Blueprint:
    store = getattr(request.app.state, "blueprints", None)
    if store is not None and blueprint_id in store:
        return cast(Blueprint, store[blueprint_id])
    # Fallback to Redis (MCP stores blueprints there)
    redis = get_redis()
    raw_json = await redis.hget(f"bp:{blueprint_id}", "json")  # type: ignore[arg-type]
    if not raw_json:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return Blueprint.model_validate_json(raw_json)


async def _run_workflow_async(
    execution_id: str,
    bp: Blueprint,
    inputs: Optional[Dict[str, Any]],
    store: Dict[str, _ExecutionRecord],
) -> None:
    """Background task that executes the workflow and updates *store*."""
    try:
        service = ServiceLocator.get("workflow_execution_service")
    except KeyError:
        # Fallback: instantiate a local workflow execution service for tests/dev
        from ice_orchestrator.services.workflow_execution_service import (
            WorkflowExecutionService,
        )

        service = WorkflowExecutionService()
    record = store[execution_id]
    try:
        record["status"] = "running"
        record["_event"].set()
        # Persist running state
        redis = get_redis()
        await redis.hset(
            _exec_key(execution_id),
            mapping={"status": "running", "blueprint_id": record["blueprint_id"]},
        )

        # Attach a lightweight event emitter to reflect per-node updates into the in-memory record
        def _event_emitter(event_name: str, payload: Dict[str, Any]) -> None:
            try:
                # Minimal mapping for UI: event, node_id, status/progress
                if event_name in {
                    EventType.NODE_STARTED.value,
                    EventType.NODE_COMPLETED.value,
                    EventType.NODE_FAILED.value,
                    EventType.WORKFLOW_STARTED.value,
                    EventType.WORKFLOW_COMPLETED.value,
                }:
                    record.setdefault("events", []).append({"event": event_name, "payload": payload})  # type: ignore[attr-defined]
            except Exception:
                pass

        # Execute with event emitter if the service supports it
        try:
            result = await service.execute(
                nodes=[n.model_dump() for n in bp.nodes],  # type: ignore[list-item]
                name=f"run_{execution_id}",
                run_id=execution_id,
                event_emitter=_event_emitter,
            )
        except AttributeError:
            # Fallback to basic execution path
            result = await service.execute_blueprint(bp.nodes, inputs=inputs, name=f"run_{execution_id}")  # type: ignore[arg-type]
        record["status"] = "completed"
        record["result"] = result.model_dump() if hasattr(result, "model_dump") else result  # type: ignore[assignment]
        record["_event"].set()
        # Persist completion
        await redis.hset(
            _exec_key(execution_id),
            mapping={
                "status": "completed",
                "result": (
                    result.model_dump_json()
                    if hasattr(result, "model_dump_json")
                    else str(result)
                ),
            },
        )
    except Exception as exc:  # noqa: BLE001
        record["status"] = "failed"
        record["error"] = str(exc)
        record["_event"].set()
        # Persist failure
        try:
            redis = get_redis()
            await redis.hset(
                _exec_key(execution_id), mapping={"status": "failed", "error": str(exc)}
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
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

    blueprint = await _get_blueprint(request, blueprint_id)

    # Governance preflight: estimate cost and enforce budget
    try:
        from ice_core.utils.node_conversion import convert_node_specs
        from ice_orchestrator.config import runtime_config
        from ice_orchestrator.execution.cost_estimator import WorkflowCostEstimator

        node_cfgs = convert_node_specs(blueprint.nodes)
        estimator = WorkflowCostEstimator()
        est = estimator.estimate_workflow_cost(node_cfgs)
        env_budget = os.getenv("ORG_BUDGET_USD")
        budget_limit = (
            float(env_budget) if env_budget else runtime_config.org_budget_usd
        )
        if budget_limit is not None and est.total_avg_cost > budget_limit:
            raise HTTPException(
                status_code=402,
                detail=f"Estimated cost ${est.total_avg_cost:.2f} exceeds budget ${budget_limit:.2f}",
            )
    except HTTPException:
        raise
    except Exception:
        # Non-fatal if estimator fails
        pass

    exec_store = _get_exec_store(request)
    execution_id = str(uuid.uuid4())

    exec_store[execution_id] = cast(
        _ExecutionRecord,
        {
            "status": "pending",
            "blueprint_id": blueprint_id,
            "_event": asyncio.Event(),  # internal notification hook
        },
    )
    # Persist initial state
    redis = get_redis()
    await redis.hset(
        _exec_key(execution_id),
        mapping={"status": "pending", "blueprint_id": blueprint_id},
    )

    # Run in background – FastAPI will await task completion if lifespan ends
    asyncio.create_task(
        _run_workflow_async(execution_id, blueprint, inputs, exec_store)
    )

    return {"execution_id": execution_id}


@router.get(
    "/{execution_id}", dependencies=[Depends(rate_limit), Depends(require_auth)]
)
async def get_execution_status(
    request: Request, execution_id: str
) -> Dict[str, Any]:  # noqa: D401
    # Prefer Redis as the source of truth
    redis = get_redis()
    data = await redis.hgetall(_exec_key(execution_id))  # type: ignore[misc]
    if data:
        decoded: Dict[str, Any] = {
            (k.decode() if isinstance(k, (bytes, bytearray)) else k): (
                v.decode() if isinstance(v, (bytes, bytearray)) else v
            )
            for k, v in data.items()
        }
        return decoded
    # Fallback to in-memory
    store = _get_exec_store(request)
    if execution_id not in store:
        raise HTTPException(status_code=404, detail="Execution not found")
    record = store[execution_id]
    return {k: v for k, v in record.items() if not k.startswith("_")}


@router.get("/", dependencies=[Depends(rate_limit), Depends(require_auth)])
async def list_executions(request: Request) -> Dict[str, Any]:  # noqa: D401
    """List known executions from Redis (authoritative) with basic fields."""
    # We don't have a native Redis scan in stub; rely on in-memory store if present
    store = _get_exec_store(request)
    results = []
    for exec_id, rec in store.items():
        results.append(
            {
                "execution_id": exec_id,
                "status": rec.get("status", "unknown"),
                "blueprint_id": rec.get("blueprint_id", ""),
            }
        )
    return {"executions": results}


@router.post(
    "/{execution_id}/cancel", dependencies=[Depends(rate_limit), Depends(require_auth)]
)
async def cancel_execution(
    request: Request, execution_id: str
) -> Dict[str, Any]:  # noqa: D401
    """Best-effort cancel of a running execution.

    MVP semantics: mark status as failed with reason="canceled" and persist.
    """
    store = _get_exec_store(request)
    if execution_id not in store:
        # Also check Redis if needed
        redis = get_redis()
        data = await redis.hgetall(_exec_key(execution_id))  # type: ignore[misc]
        if not data:
            raise HTTPException(status_code=404, detail="Execution not found")
        # Update Redis state only (no in-memory record)
        await redis.hset(
            _exec_key(execution_id), mapping={"status": "failed", "error": "canceled"}
        )
        return {"status": "canceled"}

    # Update in-memory and notify WS clients
    rec = store[execution_id]
    rec["status"] = "failed"
    rec["error"] = "canceled"
    if "_event" in rec:
        rec["_event"].set()  # type: ignore[operator]
    # Persist to Redis
    redis = get_redis()
    await redis.hset(
        _exec_key(execution_id), mapping={"status": "failed", "error": "canceled"}
    )
    return {"status": "canceled"}
    # Prefer Redis as the source of truth
    redis = get_redis()
    data = await redis.hgetall(_exec_key(execution_id))  # type: ignore[misc]
    if data:
        # Decode bytes to str if needed (aioredis returns bytes)
        decoded: Dict[str, Any] = {
            (k.decode() if isinstance(k, (bytes, bytearray)) else k): (
                v.decode() if isinstance(v, (bytes, bytearray)) else v
            )
            for k, v in data.items()
        }
        return decoded
    # Fallback to in-memory
    store = _get_exec_store(request)
    if execution_id not in store:
        raise HTTPException(status_code=404, detail="Execution not found")
    record = store[execution_id]
    return {k: v for k, v in record.items() if not k.startswith("_")}
