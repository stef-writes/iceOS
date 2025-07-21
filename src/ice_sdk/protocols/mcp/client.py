"""Async helper for the internal MCP HTTP API.

Example::

    from ice_core.models.mcp import Blueprint, NodeSpec
    from ice_sdk.protocols.mcp.client import MCPClient

    client = MCPClient()
    bp = Blueprint(nodes=[NodeSpec(id="echo", type="tool", command="echo hi")])
    ack = await client.create_blueprint(bp)
    run = await client.start_run(blueprint_id=ack.blueprint_id)
    result = await client.await_result(run.run_id)
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx

from ice_core.models.mcp import Blueprint, BlueprintAck, RunAck, RunRequest, RunResult

__all__ = ["MCPClient"]


class MCPClient:  # – thin wrapper
    def __init__(self, base_url: str | None = None, *, timeout: float = 30.0) -> None:
        self.base_url = base_url or os.getenv("ICEOS_API", "http://localhost:8000")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Blueprint helpers -------------------------------------------------
    # ------------------------------------------------------------------
    async def create_blueprint(self, blueprint: Blueprint) -> BlueprintAck:
        url = f"{self.base_url}/api/v1/mcp/blueprints"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=blueprint.model_dump(mode="json"))
            resp.raise_for_status()
            return BlueprintAck.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Run helpers -------------------------------------------------------
    # ------------------------------------------------------------------
    async def start_run(
        self,
        *,
        blueprint_id: str | None = None,
        blueprint: Blueprint | None = None,
        max_parallel: int = 5,
    ) -> RunAck:
        from ice_core.models.mcp import RunOptions

        req = RunRequest(
            blueprint_id=blueprint_id,
            blueprint=blueprint,
            options=RunOptions(max_parallel=max_parallel),
        )
        url = f"{self.base_url}/api/v1/mcp/runs"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=req.model_dump(mode="json"))
            resp.raise_for_status()
            return RunAck.model_validate(resp.json())

    async def get_result(self, run_id: str) -> Optional[RunResult]:
        url = f"{self.base_url}/api/v1/mcp/runs/{run_id}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params={"wait": False})
            if resp.status_code == 202:
                return None
            resp.raise_for_status()
            return RunResult.model_validate(resp.json())

    async def await_result(self, run_id: str, poll_interval: float = 0.5) -> RunResult:
        while True:
            res = await self.get_result(run_id)
            if res is not None:
                return res
            await asyncio.sleep(poll_interval)
