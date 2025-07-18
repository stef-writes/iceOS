"""MCP (Model Context Protocol) HTTP endpoint – minimal alpha implementation.

Exposes three operations required for the Frosty ➔ iceOS control-plane loop:
1. POST /blueprints – register or upsert a workflow blueprint.
2. POST /runs       – execute a blueprint (by id or inline).
3. GET  /runs/{id}  – fetch final result (202 while running).
4. GET  /runs/{id}/events – SSE telemetry (stub – plain text for now).

The data models intentionally mirror the draft YAML spec so we can generate
OpenAPI later with *fastapi.openapi.utils.get_openapi*.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ice_orchestrator.workflow import Workflow

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])

# ---------------------------------------------------------------------------
# Pydantic models – kept tiny for alpha -------------------------------------
# ---------------------------------------------------------------------------


class NodeSpec(BaseModel):
    """JSON-friendly node description (same keys as NodeConfig)."""

    id: str
    type: str

    # Accept arbitrary extra fields so callers can embed the full NodeConfig.
    model_config = {"extra": "allow"}


class Blueprint(BaseModel):
    """A design-time workflow blueprint."""

    blueprint_id: str = Field(default_factory=lambda: f"bp_{uuid.uuid4().hex[:8]}")
    version: str = "1.0.0"
    nodes: List[NodeSpec]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BlueprintAck(BaseModel):
    blueprint_id: str
    status: str = "accepted"


class RunOptions(BaseModel):
    max_parallel: int = Field(5, ge=1, le=20)


class RunRequest(BaseModel):
    blueprint_id: Optional[str] = None
    blueprint: Optional[Blueprint] = None
    options: RunOptions = Field(default_factory=lambda: RunOptions(max_parallel=5))

    model_config = {"extra": "forbid"}


class RunAck(BaseModel):
    run_id: str
    status_endpoint: str
    events_endpoint: str


class RunResult(BaseModel):
    run_id: str
    success: bool
    start_time: _dt.datetime
    end_time: _dt.datetime
    output: Dict[str, Any]
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# In-memory stores – good enough for MVP; swap with DB / Redis later --------
# ---------------------------------------------------------------------------

_BLUEPRINTS: Dict[str, Blueprint] = {}
_RUNS: Dict[str, RunResult] = {}
_EVENTS: Dict[str, List[str]] = {}


# ---------------------------------------------------------------------------
# Routes --------------------------------------------------------------------
# ---------------------------------------------------------------------------


@router.post(
    "/blueprints", response_model=BlueprintAck, status_code=status.HTTP_201_CREATED
)
async def create_blueprint(bp: Blueprint) -> BlueprintAck:  # noqa: D401
    """Register (or upsert) a *Blueprint*."""

    _BLUEPRINTS[bp.blueprint_id] = bp
    return BlueprintAck(blueprint_id=bp.blueprint_id, status="accepted")


@router.post("/runs", response_model=RunAck, status_code=status.HTTP_202_ACCEPTED)
async def start_run(req: RunRequest) -> RunAck:  # noqa: D401
    """Execute a blueprint by *id* or inline definition and return *run_id*."""

    if req.blueprint is None and req.blueprint_id is None:
        raise HTTPException(
            status_code=400, detail="'blueprint' or 'blueprint_id' required"
        )

    # Resolve blueprint object ------------------------------------------------
    bp = req.blueprint or _BLUEPRINTS.get(req.blueprint_id)  # type: ignore[arg-type]
    if bp is None:
        raise HTTPException(status_code=404, detail="blueprint_id not found")

    # Convert NodeSpec list into proper SkillNodeConfig / LLMOperatorConfig objects --------------
    from ice_sdk.models.node_models import (  # type: ignore
        LLMOperatorConfig,
        ConditionNodeConfig,
        NodeConfig,
        SkillNodeConfig,
    )

    conv_nodes: list[NodeConfig] = []
    for ns in bp.nodes:
        payload = ns.model_dump()
        node_type = payload.get("type")
        try:
            if node_type == "tool":
                conv_nodes.append(SkillNodeConfig.model_validate(payload))
            elif node_type == "ai":
                conv_nodes.append(LLMOperatorConfig.model_validate(payload))
            elif node_type == "condition":
                conv_nodes.append(ConditionNodeConfig.model_validate(payload))
            else:
                raise ValueError(f"Unknown node type '{node_type}'")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid node spec: {exc}")

    chain = Workflow(
        nodes=conv_nodes, name=bp.blueprint_id, max_parallel=req.options.max_parallel
    )

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    start_ts = _dt.datetime.utcnow()

    try:
        result_obj = await chain.execute()
        success = result_obj.success
        output = result_obj.output or {}  # type: ignore[arg-type]
        error_msg: str | None = result_obj.error
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
    _EVENTS.setdefault(run_id, []).append(
        f'event: run_finished\ndata: {{"run_id":"{run_id}", "success": {str(success).lower()} }}\n'
    )

    return RunAck(
        run_id=run_id,
        status_endpoint=f"/api/v1/mcp/runs/{run_id}",
        events_endpoint=f"/api/v1/mcp/runs/{run_id}/events",
    )


@router.get("/runs/{run_id}", response_model=RunResult)
async def get_result(run_id: str) -> RunResult:  # noqa: D401
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
    ) -> EventSourceResponse:  # noqa: D401 – async generator
        """Stream events for *run_id* via Server-Sent Events."""

        queue = _EVENTS.get(run_id)
        if queue is None:
            raise HTTPException(status_code=404, detail="run_id not found")

        async def _gen() -> AsyncGenerator[str, None]:  # noqa: D401 – async generator
            idx = 0
            while True:
                if idx < len(queue):
                    yield queue[idx]
                    idx += 1
                else:
                    await asyncio.sleep(0.1)
                    # Break when run finished and all events delivered
                    if _RUNS.get(run_id) is not None:
                        break

        return EventSourceResponse(_gen())

except ImportError:  # pragma: no cover – SSE optional

    from typing import Any  # Imported here to avoid unconditional dependency

    @router.get("/runs/{run_id}/events")
    async def event_stream_plain(run_id: str) -> Any:  # noqa: D401
        """Fallback plain text when *sse_starlette* is missing."""

        from fastapi.responses import PlainTextResponse

        events = _EVENTS.get(run_id)
        if events is None:
            raise HTTPException(status_code=404, detail="run_id not found")
        body = "\n\n".join(events)
        return PlainTextResponse(body, media_type="text/event-stream")
