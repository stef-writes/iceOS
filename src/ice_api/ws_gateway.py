"""WebSocket gateway for MCP realtime patch & telemetry streams.

This initial version supports:
* Client → server: canvas **patch** events.
* Server → client: **telemetry**, **suggestion**, **cursor** events.

Authentication: simple bearer token via `Sec-WebSocket-Protocol` header.
Validation: every incoming JSON payload validated against a registry of
`jsonschema` Draft 2020-12 schemas.

The gateway stays stateless: it forwards valid messages to an
`asyncio.Queue` for later consumption by Frosty agents and broadcasts
runtime events pushed into the same queue.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.websockets import WebSocketState
from jsonschema import Draft202012Validator

router = APIRouter(prefix="/ws/mcp", tags=["mcp"])

# ---------------------------------------------------------------------------
# Simple bearer-token auth helper
# ---------------------------------------------------------------------------

def _auth_token() -> str:
    return os.getenv("ICE_WS_BEARER", "dev-token")

def _assert_auth(ws: WebSocket) -> None:
    proto = ws.headers.get("sec-websocket-protocol")
    if proto != _auth_token():
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)

# ---------------------------------------------------------------------------
# JSONSchema registry --------------------------------------------------------
# ---------------------------------------------------------------------------
_SCHEMAS: dict[str, dict[str, Any]] = {
    "patch_node": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "t": {"const": "patch_node"},
            "node_id": {"type": "string"},
            "field": {"type": "string"},
            "value": {},
        },
        "required": ["t", "node_id", "field", "value"],
        "additionalProperties": False,
    },
    "telemetry": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "t": {"const": "telemetry"},
            "node_id": {"type": "string"},
            "latency_ms": {"type": "number"},
            "cost": {"type": "number"},
        },
        "required": ["t", "node_id", "latency_ms", "cost"],
        "additionalProperties": True,
    },
    "cursor": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "t": {"const": "cursor"},
            "user": {"type": "string"},
            "x": {"type": "number"},
            "y": {"type": "number"},
        },
        "required": ["t", "user", "x", "y"],
        "additionalProperties": False,
    },
}

_VALIDATORS = {name: Draft202012Validator(schema) for name, schema in _SCHEMAS.items()}

# ---------------------------------------------------------------------------
# Broadcast infrastructure (naïve asyncio queues) ----------------------------
# ---------------------------------------------------------------------------
_clients: set[WebSocket] = set()
_broadcast_q: asyncio.Queue[str] = asyncio.Queue()

async def _broadcast_worker() -> None:
    """Background task: pop messages from queue and fan-out to clients."""
    while True:
        msg = await _broadcast_q.get()
        disconnected: list[WebSocket] = []
        for ws in _clients:
            if ws.application_state == WebSocketState.CONNECTED:
                try:
                    await ws.send_text(msg)
                except Exception:
                    disconnected.append(ws)
        for dead in disconnected:
            _clients.discard(dead)

aio_bg_task: asyncio.Task[None] | None = None

@router.websocket("/")
async def mcp_ws(ws: WebSocket) -> None:  # – FastAPI handler
    """Bidirectional WS endpoint for live patch + telemetry messages."""

    await ws.accept(subprotocol=_auth_token())
    try:
        _assert_auth(ws)
    except WebSocketDisconnect:
        return

    global aio_bg_task  # – single global background task
    if aio_bg_task is None:
        aio_bg_task = asyncio.create_task(_broadcast_worker())

    _clients.add(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
                msg_type: str = data.get("t", "")
                validator = _VALIDATORS.get(msg_type)
                if validator is None:
                    await ws.send_text(json.dumps({"error": "unknown message type"}))
                    continue
                validator.validate(data)
            except Exception as exc:  # schema error or JSON error
                await ws.send_text(json.dumps({"error": str(exc)}))
                continue

            # Attach message id & timestamp
            data["mid"] = uuid.uuid4().hex
            data["ts"] = asyncio.get_event_loop().time()
            await _broadcast_q.put(json.dumps(data))
    finally:
        _clients.discard(ws)
