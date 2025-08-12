"""WebSocket endpoint for live execution updates."""

from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


def _public_view(record: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in record.items() if not k.startswith("_")}


@router.websocket("/executions/{execution_id}")
async def websocket_execution_updates(websocket: WebSocket, execution_id: str) -> None:  # noqa: D401
    await websocket.accept()

    app = websocket.app  # FastAPI app instance
    exec_store = getattr(app.state, "executions", {})

    if execution_id not in exec_store:
        await websocket.send_json({"error": "Execution not found"})
        await websocket.close(code=4404)
        return

    record = exec_store[execution_id]
    # Send initial snapshot
    await websocket.send_json(_public_view(record))

    try:
        while True:
            # Wait for an update event
            await record["_event"].wait()
            record["_event"].clear()
            payload = _public_view(record)
            await websocket.send_text(json.dumps(payload))
            if record["status"] in {"completed", "failed"}:
                await websocket.close()
                break
    except WebSocketDisconnect:
        # Client disconnected – nothing to clean up
        pass
