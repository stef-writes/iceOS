"""Execution management REST endpoints."""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ice_api.redis_client import get_redis
from ice_core.models.mcp import Blueprint


# Duplicate event names locally to avoid app→orchestrator import
class _Evt:
    NODE_STARTED = "node.started"
    NODE_COMPLETED = "node.completed"
    NODE_FAILED = "node.failed"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"


router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


class ExecutionStartResponse(BaseModel):
    """Response for starting a workflow execution.

    Args:
        execution_id (str): Identifier for the created execution.
        status (str): Current status (accepted, running, completed, failed, timeout).
        result (Dict[str, Any] | None): Final result when completed.

    Returns:
        ExecutionStartResponse: Response model containing execution details.
    """

    execution_id: str
    status: str
    result: Optional[Dict[str, Any]] = None


class ExecutionStatusResponse(BaseModel):
    """Response model for execution status."""

    execution_id: str
    status: str
    blueprint_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    events: Optional[List[Dict[str, Any]]] = None


class ExecutionsListItem(BaseModel):
    execution_id: str
    status: str
    blueprint_id: str


class ExecutionsListResponse(BaseModel):
    executions: List[ExecutionsListItem]


class ExecutionStartRequest(BaseModel):
    """Request body to start a workflow execution.

    Args:
        blueprint_id (str): Identifier of a previously stored blueprint.
        inputs (Dict[str, Any] | None): Optional initial inputs passed to the workflow.

    Returns:
        None
    """

    blueprint_id: str = Field(..., description="Stored blueprint id")
    inputs: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional initial inputs for the workflow"
    )


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
    # Resolve workflow execution service via runtime factories when available
    try:
        from importlib import import_module

        WorkflowExecutionService = getattr(
            import_module("ice_orchestrator.services.workflow_execution_service"),
            "WorkflowExecutionService",
        )
        service = WorkflowExecutionService()
    except Exception:
        # In minimal builds orchestrator may be unavailable
        raise RuntimeError("Orchestrator runtime not available")
    record = store[execution_id]
    try:
        record["status"] = "running"
        record["_event"].set()
        # Persist running state
        try:
            redis = get_redis()
            await redis.hset(
                _exec_key(execution_id),
                mapping={"status": "running", "blueprint_id": record["blueprint_id"]},
            )
        except Exception:
            pass

        # Attach a lightweight event emitter to reflect per-node updates into the in-memory record
        def _event_emitter(event_name: str, payload: Dict[str, Any]) -> None:
            try:
                # Minimal mapping for UI: event, node_id, status/progress
                if event_name in {
                    _Evt.NODE_STARTED,
                    _Evt.NODE_COMPLETED,
                    _Evt.NODE_FAILED,
                    _Evt.WORKFLOW_STARTED,
                    _Evt.WORKFLOW_COMPLETED,
                }:
                    record.setdefault("events", []).append(
                        {"event": event_name, "payload": payload}
                    )  # type: ignore[attr-defined]
            except Exception:
                pass

        # Execute with event emitter if the service supports it
        try:
            # Preferred path: execute from NodeSpec list
            result = await service.execute_blueprint(
                bp.nodes,
                inputs=inputs,
                name=f"run_{execution_id}",
            )
        except Exception:
            # As a last resort, construct a Workflow and execute
            from importlib import import_module

            Workflow = getattr(import_module("ice_orchestrator.workflow"), "Workflow")
            from ice_core.utils.node_conversion import convert_node_specs

            wf = Workflow(
                nodes=convert_node_specs(bp.nodes), name=f"run_{execution_id}"
            )
            result = await service.execute_workflow(wf, inputs=inputs)
        record["status"] = "completed"
        record["result"] = (
            result.model_dump() if hasattr(result, "model_dump") else result
        )  # type: ignore[assignment]
        record["_event"].set()
        # Persist completion
        try:
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
            try:
                import os as _os

                exec_ttl = int(_os.getenv("EXECUTION_TTL_SECONDS", "0"))
                if exec_ttl > 0 and hasattr(redis, "expire"):
                    await redis.expire(_exec_key(execution_id), exec_ttl)  # type: ignore[misc]
            except Exception:
                pass
        except Exception:
            pass
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
            try:
                import os as _os

                exec_ttl = int(_os.getenv("EXECUTION_TTL_SECONDS", "0"))
                if exec_ttl > 0 and hasattr(redis, "expire"):
                    await redis.expire(_exec_key(execution_id), exec_ttl)  # type: ignore[misc]
            except Exception:
                pass
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
    payload: ExecutionStartRequest = Body(...),
    wait_seconds: float | None = Query(
        default=None,
        description=(
            "Optional: block up to N seconds and return final status/result instead of an execution_id."
        ),
    ),
) -> "ExecutionStartResponse":
    """Kick off a workflow execution.

    Expected JSON body::
        {
            "blueprint_id": "...",            # required
            "inputs": {...}                     # optional initial inputs
        }
    """

    blueprint_id = payload.blueprint_id
    inputs = payload.inputs

    blueprint = await _get_blueprint(request, blueprint_id)

    # Governance preflight: estimate cost and enforce budget
    try:
        from importlib import import_module

        from ice_core.utils.node_conversion import convert_node_specs

        runtime_config = getattr(
            import_module("ice_orchestrator.config"), "runtime_config"
        )
        WorkflowCostEstimator = getattr(
            import_module("ice_orchestrator.execution.cost_estimator"),
            "WorkflowCostEstimator",
        )

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
    # Persist initial state (fallback to in-memory when Redis unavailable)
    try:
        redis = get_redis()
        await redis.hset(
            _exec_key(execution_id),
            mapping={"status": "pending", "blueprint_id": blueprint_id},
        )
        try:
            import os as _os

            exec_ttl = int(_os.getenv("EXECUTION_TTL_SECONDS", "0"))
            if exec_ttl > 0 and hasattr(redis, "expire"):
                await redis.expire(_exec_key(execution_id), exec_ttl)  # type: ignore[misc]
        except Exception:
            pass
    except Exception:
        pass

    # Run in background – FastAPI will await task completion if lifespan ends
    asyncio.create_task(
        _run_workflow_async(execution_id, blueprint, inputs, exec_store)
    )

    # Optional synchronous waiting for simpler client UX ---------------------
    if wait_seconds and wait_seconds > 0:
        deadline = asyncio.get_event_loop().time() + wait_seconds
        # Poll minimal state until terminal or timeout
        while asyncio.get_event_loop().time() < deadline:
            rec = exec_store.get(execution_id, {})
            status_val = rec.get("status")
            if status_val in {"completed", "failed"}:
                return ExecutionStartResponse(
                    execution_id=execution_id,
                    status=str(status_val),
                    result=(
                        rec["result"] if isinstance(rec.get("result"), dict) else None
                    ),
                )
            await asyncio.sleep(0.2)
        # Timed out – return the id so clients can poll later
        return ExecutionStartResponse(
            execution_id=execution_id,
            status=str(exec_store[execution_id].get("status", "pending")),
        )

    return ExecutionStartResponse(execution_id=execution_id, status="accepted")


@router.get(
    "/{execution_id}", dependencies=[Depends(rate_limit), Depends(require_auth)]
)
async def get_execution_status(
    request: Request, execution_id: str
) -> ExecutionStatusResponse:  # noqa: D401
    # Prefer Redis as the source of truth; on error, fall back to in-memory
    try:
        redis = get_redis()
        from typing import Any as _Any  # local alias for type annotation clarity

        data: Dict[_Any, _Any] = await redis.hgetall(_exec_key(execution_id))  # type: ignore[misc]
        if data:
            decoded: Dict[str, Any] = {}
            for k, v in data.items():
                key = (
                    k
                    if isinstance(k, str)
                    else (k.decode() if isinstance(k, (bytes, bytearray)) else str(k))
                )
                if isinstance(v, (bytes, bytearray)):
                    try:
                        val_decoded = v.decode()
                    except Exception:
                        val_decoded = None
                    decoded[key] = val_decoded if val_decoded is not None else str(v)
                else:
                    decoded[key] = v
            # Normalize JSON fields
            try:
                import json as _json

                if isinstance(decoded.get("result"), str):
                    val = decoded.get("result")
                    if isinstance(val, str) and val and val[0] in "[{":
                        decoded["result"] = _json.loads(val)
            except Exception:
                pass
            return ExecutionStatusResponse(
                execution_id=execution_id,
                status=str(decoded.get("status", "unknown")),
                blueprint_id=(
                    str(decoded.get("blueprint_id"))
                    if decoded.get("blueprint_id")
                    else None
                ),
                result=(
                    decoded["result"]
                    if ("result" in decoded and isinstance(decoded.get("result"), dict))
                    else None
                ),
                error=str(decoded.get("error")) if decoded.get("error") else None,
                events=(
                    decoded["events"]
                    if ("events" in decoded and isinstance(decoded.get("events"), list))
                    else None
                ),
            )
    except Exception:
        # Ignore Redis connectivity issues
        pass
    # Fallback to in-memory
    store = _get_exec_store(request)
    if execution_id not in store:
        raise HTTPException(status_code=404, detail="Execution not found")
    record = store[execution_id]
    public = {k: v for k, v in record.items() if not k.startswith("_")}
    result_val: Optional[Dict[str, Any]] = None
    _rv = public.get("result")
    if isinstance(_rv, dict):
        from typing import cast as _cast

        result_val = _cast(Dict[str, Any], _rv)
    events_val: Optional[List[Dict[str, Any]]] = None
    _ev = public.get("events")
    if isinstance(_ev, list) and all(isinstance(e, dict) for e in _ev):
        from typing import cast as _cast

        events_val = _cast(List[Dict[str, Any]], _ev)
    return ExecutionStatusResponse(
        execution_id=execution_id,
        status=str(public.get("status", "unknown")),
        blueprint_id=str(public.get("blueprint_id"))
        if public.get("blueprint_id")
        else None,
        result=result_val,
        error=str(public.get("error")) if public.get("error") else None,
        events=events_val,
    )


@router.get("/", dependencies=[Depends(rate_limit), Depends(require_auth)])
async def list_executions(request: Request) -> ExecutionsListResponse:  # noqa: D401
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
    return ExecutionsListResponse(
        executions=[
            ExecutionsListItem(
                execution_id=rec["execution_id"],
                status=rec["status"],
                blueprint_id=rec["blueprint_id"],
            )
            for rec in results
        ]
    )


@router.post(
    "/{execution_id}/cancel", dependencies=[Depends(rate_limit), Depends(require_auth)]
)
async def cancel_execution(request: Request, execution_id: str) -> Dict[str, Any]:  # noqa: D401
    """Best-effort cancel of a running execution.

    MVP semantics: mark status as failed with reason="canceled" and persist.
    """
    store = _get_exec_store(request)
    if execution_id not in store:
        # Also check Redis if needed
        try:
            redis = get_redis()
            data = await redis.hgetall(_exec_key(execution_id))  # type: ignore[misc]
            if not data:
                raise HTTPException(status_code=404, detail="Execution not found")
            # Update Redis state only (no in-memory record)
            await redis.hset(
                _exec_key(execution_id),
                mapping={"status": "failed", "error": "canceled"},
            )
            return {"status": "canceled"}
        except HTTPException:
            raise
        except Exception:
            # Redis unavailable and no in-memory record
            raise HTTPException(status_code=404, detail="Execution not found")

    # Update in-memory and notify WS clients
    rec = store[execution_id]
    rec["status"] = "failed"
    rec["error"] = "canceled"
    if "_event" in rec:
        rec["_event"].set()  # type: ignore[operator]
    # Persist to Redis (best effort)
    try:
        redis = get_redis()
        await redis.hset(
            _exec_key(execution_id), mapping={"status": "failed", "error": "canceled"}
        )
    except Exception:
        pass
    return {"status": "canceled"}
