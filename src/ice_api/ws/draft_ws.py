"""WebSocket endpoint that streams DraftState updates."""
from __future__ import annotations

import json
from typing import Dict, List, Set

from fastapi import WebSocket, WebSocketDisconnect

from ice_core.models.draft import DraftState

_active_clients: Dict[str, Set[WebSocket]] = {}

async def register(session_id: str, ws: WebSocket) -> None:  # noqa: D401
    await ws.accept()
    _active_clients.setdefault(session_id, set()).add(ws)

async def unregister(session_id: str, ws: WebSocket) -> None:  # noqa: D401
    _active_clients.get(session_id, set()).discard(ws)

async def broadcast(session_id: str, state: DraftState) -> None:  # noqa: D401
    """Send *state* to every client subscribed to *session_id*."""
    if session_id not in _active_clients:
        return
    data = json.dumps({
        "mermaid": state.mermaid_versions[-1] if state.mermaid_versions else "",
        "meta": state.meta,
    })
    disconnected: List[WebSocket] = []
    for ws in _active_clients[session_id]:
        try:
            await ws.send_text(data)
        except WebSocketDisconnect:
            disconnected.append(ws)
    for ws in disconnected:
        await unregister(session_id, ws)