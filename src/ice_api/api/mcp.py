"""MCP (Model Context Protocol) HTTP endpoint – complete implementation.

Exposes three operations required for the Frosty ➔ iceOS control-plane loop:
1. POST /blueprints – register or upsert a workflow blueprint.
2. POST /runs       – execute a blueprint (by id or inline).
3. GET  /runs/{id}  – fetch final result (202 while running).
4. GET  /runs/{id}/events – SSE telemetry (stub – plain text for now).

The data models intentionally mirror the draft YAML spec so we can generate
OpenAPI later with *fastapi.openapi.utils.get_openapi*.
"""

from __future__ import annotations

import datetime as _dt
import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status

# Redis helper
from ice_api.redis_client import get_redis
from ice_core.models.mcp import Blueprint, BlueprintAck, RunAck, RunRequest, RunResult
from ice_core.services.contracts import IWorkflowService
from ice_sdk.services.locator import ServiceLocator


# Fetch service lazily to avoid bootstrap order problems --------------------
def _get_workflow_service() -> IWorkflowService:
    return ServiceLocator.get("workflow_service")  # type: ignore[return-value]


router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])

# ---------------------------------------------------------------------------
# In-memory stores – good enough for MVP; swap with DB / Redis later --------
# ---------------------------------------------------------------------------

# In-memory fallback stores (only for unit-tests) ---------------------------
_RUNS: Dict[str, RunResult] = {}
_EVENTS: Dict[str, List[str]] = {}

# Redis keys helpers --------------------------------------------------------


def _bp_key(bp_id: str) -> str:
    return f"bp:{bp_id}"


def _stream_key(run_id: str) -> str:
    return f"stream:{run_id}"


# ---------------------------------------------------------------------------
# Routes --------------------------------------------------------------------
# ---------------------------------------------------------------------------


@router.post(
    "/blueprints", response_model=BlueprintAck, status_code=status.HTTP_201_CREATED
)
async def create_blueprint(bp: Blueprint) -> BlueprintAck:
    """Register (or upsert) a *Blueprint*."""

    # Validate nodes before persisting
    try:
        bp.validate_runtime()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid blueprint: {exc}")

    redis = get_redis()
    await redis.hset(_bp_key(bp.blueprint_id), mapping={"json": bp.model_dump_json()})
    return BlueprintAck(blueprint_id=bp.blueprint_id, status="accepted")


@router.post("/runs", response_model=RunAck, status_code=status.HTTP_202_ACCEPTED)
async def start_run(req: RunRequest) -> RunAck:
    """Execute a blueprint by *id* or inline definition and return *run_id*."""

    if req.blueprint is None and req.blueprint_id is None:
        raise HTTPException(
            status_code=400, detail="'blueprint' or 'blueprint_id' required"
        )

    # Resolve blueprint object ------------------------------------------------
    bp: Optional[Blueprint]
    if req.blueprint is not None:
        bp = req.blueprint
    else:
        redis = get_redis()
        raw_json = await redis.hget(_bp_key(req.blueprint_id), "json")  # type: ignore[arg-type]
        bp = Blueprint.model_validate_json(raw_json) if raw_json else None
    if bp is None:
        raise HTTPException(status_code=404, detail="blueprint_id not found")

    # Validate (and implicitly convert) the blueprint -------------------------
    try:
        bp.validate_runtime()
        from ice_core.utils.node_conversion import convert_node_specs

        conv_nodes = convert_node_specs(bp.nodes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid node spec: {exc}")

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    start_ts = _dt.datetime.utcnow()

    try:
        redis = get_redis()

        # Event emitter closure ---------------------------------------
        def _emit(evt_name: str, payload: dict) -> None:
            redis.xadd(_stream_key(run_id), {"event": evt_name, "payload": json.dumps(payload)})  # type: ignore[arg-type]

        result_obj = await _get_workflow_service().execute(
            conv_nodes,
            bp.blueprint_id,
            req.options.max_parallel,
            run_id=run_id,
            event_emitter=_emit,
        )
        from pydantic import BaseModel

        def _serialize(obj):
            """Recursively convert Pydantic models to plain dicts."""
            if isinstance(obj, BaseModel):
                return obj.model_dump()
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_serialize(x) for x in obj]
            return obj

        success = result_obj.get("success", False)
        output = _serialize(result_obj.get("output", {}))
        error_msg: str | None = result_obj.get("error")
    except Exception as exc:  # pragma: no cover – runtime failure fallback
        success = False
        output = {}
        error_msg = str(exc)

    end_ts = _dt.datetime.utcnow()

    run_result = RunResult(
        run_id=run_id,
        success=success,
        start_time=start_ts,
        end_time=end_ts,
        output=output,
        error=error_msg,
    )
    _RUNS[run_id] = run_result
    # Pre-populate first event (finished) so SSE clients receive something.
    # Push terminal event to stream
    await redis.xadd(
        _stream_key(run_id),
        {
            "event": "workflow.finished",
            "payload": json.dumps({"run_id": run_id, "success": success}),
        },
    )

    return RunAck(
        run_id=run_id,
        status_endpoint=f"/api/v1/mcp/runs/{run_id}",
        events_endpoint=f"/api/v1/mcp/runs/{run_id}/events",
    )


@router.get("/runs/{run_id}", response_model=RunResult)
async def get_result(run_id: str) -> RunResult:
    """Return the final *RunResult* if available, else 202."""

    result = _RUNS.get(run_id)
    if result is None:
        raise HTTPException(
            status_code=202, detail="Run is still executing or not found"
        )
    return result


try:
    from collections.abc import AsyncGenerator

    from sse_starlette.sse import EventSourceResponse  # type: ignore

    @router.get("/runs/{run_id}/events")
    async def event_stream(
        run_id: str,
    ) -> EventSourceResponse:  # – async generator
        """Stream events for *run_id* via Server-Sent Events."""

        redis = get_redis()

        stream = _stream_key(run_id)
        # Check stream exists
        exists = await redis.exists(stream)
        if not exists:
            raise HTTPException(status_code=404, detail="run_id not found")

        async def _gen() -> AsyncGenerator[str, None]:
            last_id: str = "0-0"
            while True:
                events = await redis.xread({stream: last_id}, block=1000, count=10)  # type: ignore[arg-type]
                if events:
                    for _, batches in events:
                        for ev_id, data in batches:
                            last_id = ev_id
                            yield f"event: {data['event']}\ndata: {data['payload']}\n\n"
                            if data.get("event") == "workflow.finished":
                                return

        return EventSourceResponse(_gen())

except ImportError:  # pragma: no cover – SSE optional

    from typing import Any  # Imported here to avoid unconditional dependency

    @router.get("/runs/{run_id}/events")
    async def event_stream_plain(run_id: str) -> Any:
        """Fallback plain text when *sse_starlette* is missing."""

        from fastapi.responses import PlainTextResponse

        events = _EVENTS.get(run_id)
        if events is None:
            raise HTTPException(status_code=404, detail="run_id not found")
        body = "\n\n".join(events)
        return PlainTextResponse(body, media_type="text/event-stream")
