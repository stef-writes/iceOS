"""Mock HTTP bin tool.

Starts a lightweight FastAPI server on an ephemeral local port so other
workflow nodes can POST data during local development/testing.  All posted
items are stored in memory and can be retrieved via GET.
"""
from __future__ import annotations

import asyncio
import contextlib
import socket
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import APIRouter, FastAPI, status
from pydantic import Field

from ice_core.base_tool import ToolBase


def _find_free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        from typing import cast
        return cast(int, s.getsockname()[1])


class MockHTTPBinTool(ToolBase):
    """Spin up an in-process HTTP bin and return its URL."""

    name: str = "mock_http_bin"
    description: str = "Launch a local FastAPI server that stores posted JSON payloads"

    async def _execute_impl(
        self,
        *,
        port: Optional[int] = None,
    ) -> Dict[str, Any]:
        port = port or _find_free_port()

        app = FastAPI(title="Mock HTTP Bin", docs_url=None, redoc_url=None)
        router = APIRouter()
        store: List[Dict[str, Any]] = []

        @router.post("/items", status_code=status.HTTP_201_CREATED)
        async def create_item(item: Dict[str, Any]) -> Dict[str, Any]:  # noqa: D401
            store.append(item)
            return {"status": "accepted", "index": len(store) - 1}

        @router.get("/items", response_model=List[Dict[str, Any]])
        async def list_items() -> List[Dict[str, Any]]:  # noqa: D401
            return store

        app.include_router(router)

        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")  # type: ignore[arg-type]
        server = uvicorn.Server(config)

        # Run server in the background; keep reference so GC doesn't kill it
        asyncio.create_task(server.serve())

        url = f"http://127.0.0.1:{port}/items"
        return {"url": url}


# Auto-register ---------------------------------------------------------------
from ice_core.unified_registry import registry  # noqa: E402
from ice_core.models.enums import NodeType  # noqa: E402

_instance = MockHTTPBinTool()
registry.register_instance(NodeType.TOOL, _instance.name, _instance, validate=False)  # type: ignore[arg-type]
