"""Async client for submitting and monitoring workflows on a remote orchestrator.

Only the *public* MCP REST endpoints are used – we never import, nor do we need
access to, any of the proprietary orchestrator internals.  This keeps the IP
surface area minimal while still allowing third-party code (Frosty, Canvas, CLI
wrappers) to run workflows.

Example
-------
>>> import asyncio, json
>>> from ice_core.models.mcp import Blueprint, NodeSpec  # Only for demo
>>> from ice_client import IceClient
>>>
>>> bp = Blueprint(nodes=[NodeSpec(id="n1", type="noop")])
>>> client = IceClient("http://localhost:8000")
>>> async def _run():
...     ack = await client.submit_blueprint(bp)
...     async for event in client.stream_events(ack.run_id):
...         print("EVENT", event)
...     result = await client.wait_for_completion(ack.run_id)
...     print(json.dumps(result.output, indent=2))
>>> asyncio.run(_run())
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from enum import Enum
from types import TracebackType
from typing import Any, AsyncIterator, Final, Mapping, MutableMapping, Optional, Type

import httpx
from pydantic import ValidationError

from ice_core.models.mcp import Blueprint, RunAck, RunResult

logger = logging.getLogger(__name__)

JSON: Final = Mapping[str, Any]


class RunStatus(str, Enum):
    """Execution state returned by :py:meth:`IceClient.get_status`."""

    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


class OrchestratorError(RuntimeError):
    """Raised when the orchestrator returns an *unexpected* response."""


class IceClient:
    """Thin async wrapper around the orchestrator REST API.

    Parameters
    ----------
    base_url : str
        Root URL where the orchestrator API can be reached, *without* the
        ``/api/v1/mcp`` suffix.  Example: ``"https://orchestrator.iceos.dev"``.
    timeout : float, optional
        Per-request timeout in seconds.  Defaults to 60 seconds.
    """

    _API_PREFIX: Final[str] = "/api/v1/mcp"

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float | None = 60.0,
        auth_token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Create a client for the orchestrator API.

        If base_url is not provided, falls back to ICE_API_URL or http://localhost:8000.
        If auth_token is not provided, falls back to ICE_API_TOKEN.
        """
        resolved_base_url: str = (
            base_url
            if base_url is not None
            else os.getenv("ICE_API_URL", "http://localhost:8000")
        )
        token_env: str = os.getenv("ICE_API_TOKEN", "dev-token")
        token = (auth_token if auth_token is not None else token_env).strip()
        default_headers = {"Authorization": f"Bearer {token}"}
        self._client = httpx.AsyncClient(
            base_url=resolved_base_url,
            timeout=timeout,
            headers=default_headers,
            transport=transport,
        )

    # --------------------------------------------------------------------- ctx
    async def __aenter__(self) -> "IceClient":  # noqa: D401 (imperative mood)
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> Optional[bool]:
        await self._client.aclose()
        # Do *not* suppress exceptions – propagate them.
        return None

    # ---------------------------------------------------------------- blueprint
    async def submit_blueprint(
        self,
        blueprint: Blueprint | Mapping[str, Any] | None = None,
        /,
        *,
        blueprint_id: str | None = None,
        max_parallel: int = 5,
    ) -> RunAck:
        """Submit a workflow for asynchronous execution.

        One of *blueprint* or *blueprint_id* **must** be supplied.  When both
        are present, *blueprint* takes precedence.

        Parameters
        ----------
        blueprint : Blueprint | dict[str, Any] | None, optional
            An *inline* blueprint definition to run.
        blueprint_id : str | None, optional
            ID of a blueprint already registered on the server (see the MCP
            ``/blueprints`` endpoint).
        max_parallel : int, default=5
            Concurrency limit to pass through to the orchestrator.

        Returns
        -------
        ice_core.models.mcp.RunAck
        """

        if blueprint is None and blueprint_id is None:
            raise ValueError("Either blueprint or blueprint_id must be provided")

        payload: MutableMapping[str, Any] = {
            "options": {"max_parallel": max_parallel},
        }
        if blueprint is not None:
            payload["blueprint"] = (
                blueprint.model_dump(mode="json")
                if isinstance(blueprint, Blueprint)
                else blueprint
            )
        else:
            payload["blueprint_id"] = blueprint_id  # type: ignore[assignment]

        url = f"{self._API_PREFIX}/runs"
        resp = await self._client.post(url, json=payload)
        _raise_for_status(resp)
        data = resp.json()
        try:
            return RunAck(**data)
        except ValidationError as exc:  # pragma: no cover – unexpected schema
            raise OrchestratorError(f"Invalid RunAck payload: {exc}") from exc

    # ---------------------------------------------------------------- status
    async def get_status(self, run_id: str, /) -> tuple[RunStatus, Optional[RunResult]]:
        """Return execution status and result (if finished)."""

        url = f"{self._API_PREFIX}/runs/{run_id}"
        resp = await self._client.get(url)
        if resp.status_code == 202:
            return RunStatus.RUNNING, None
        if resp.status_code == 404:
            raise OrchestratorError(f"run_id {run_id} not found")
        _raise_for_status(resp)
        try:
            result = RunResult(**resp.json())
        except ValidationError as exc:  # pragma: no cover
            raise OrchestratorError(f"Invalid RunResult payload: {exc}") from exc
        status = RunStatus.FINISHED if result.success else RunStatus.ERROR
        return status, result

    # ---------------------------------------------------------------- blueprints
    async def create_blueprint(self, payload: Mapping[str, Any]) -> tuple[str, str]:
        """Create a blueprint via REST API and return (id, version_lock)."""
        url = "/api/v1/blueprints/"
        # Optimistic creation header required by the API
        headers = {"X-Version-Lock": "__new__"}
        resp = await self._client.post(url, json=dict(payload), headers=headers)
        _raise_for_status(resp)
        data = resp.json()
        return data["id"], data["version_lock"]

    # ---------------------------------------------------------------- executions
    async def run(
        self,
        *,
        blueprint_id: str | None = None,
        blueprint: Blueprint | Mapping[str, Any] | None = None,
        inputs: Mapping[str, Any] | None = None,
    ) -> str:
        """Start an execution. If a blueprint dict/model is provided, it will be created first."""
        bp_id = blueprint_id
        if blueprint is not None:
            from typing import cast as _cast

            payload: Mapping[str, Any]
            if isinstance(blueprint, Blueprint):
                payload = _cast(Mapping[str, Any], blueprint.model_dump(mode="json"))
            else:
                payload = blueprint  # type: ignore[assignment]
            bp_id, _ = await self.create_blueprint(payload)
        if not bp_id:
            raise ValueError("Either blueprint_id or blueprint must be provided")

        url = "/api/v1/executions/"
        body: MutableMapping[str, Any] = {
            "payload": {"blueprint_id": bp_id, "inputs": dict(inputs or {})}
        }
        resp = await self._client.post(url, json=body)
        _raise_for_status(resp)
        data: Any = resp.json()
        return str(data["execution_id"])  # ensure str type

    async def poll_until_complete(
        self,
        execution_id: str,
        *,
        poll_interval: float = 0.5,
        timeout: float | None = None,
    ) -> Mapping[str, Any]:
        """Poll the execution status until it completes or fails and return the final payload."""
        start = asyncio.get_event_loop().time()
        while True:
            resp = await self._client.get(f"/api/v1/executions/{execution_id}")
            _raise_for_status(resp)
            data: Mapping[str, Any] = resp.json()
            status = data.get("status")
            if status in {"completed", "failed"}:
                return data
            await asyncio.sleep(poll_interval)
            if timeout and (asyncio.get_event_loop().time() - start) > timeout:
                raise TimeoutError(
                    f"Execution {execution_id} did not finish within {timeout} seconds"
                )

    # ---------------------------------------------------------------- wait
    async def wait_for_completion(
        self,
        run_id: str,
        /,
        *,
        poll_interval: float = 1.5,
        timeout: float | None = None,
    ) -> RunResult:
        """Block until workflow finishes.

        Internally performs exponential back-off polling (1.5 × each attempt,
        capped at ~10 seconds) unless *timeout* is reached.
        """

        start = asyncio.get_event_loop().time()
        interval = poll_interval
        while True:
            status, result = await self.get_status(run_id)
            if status != RunStatus.RUNNING:
                assert result is not None  # mypy – already handled above
                return result
            await asyncio.sleep(interval)
            interval = min(interval * 1.5, 10.0)
            if timeout and (asyncio.get_event_loop().time() - start) > timeout:
                raise TimeoutError(
                    f"Run {run_id} did not finish within {timeout} seconds"
                )

    # ---------------------------------------------------------------- events
    async def stream_events(self, run_id: str, /) -> AsyncIterator[dict[str, Any]]:
        """Yield workflow events as soon as the server emits them.

        Relies on Server-Sent Events (SSE).  Each yielded item is the JSON
        payload originally passed to the orchestrator’s internal event emitter.
        """

        url = f"{self._API_PREFIX}/runs/{run_id}/events"
        headers = {"Accept": "text/event-stream"}

        # httpx doesn't parse SSE – do it manually.
        async with self._client.stream("GET", url, headers=headers) as resp:
            _raise_for_status(resp)
            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    try:
                        yield json.loads(line.removeprefix("data: "))
                    except json.JSONDecodeError:  # pragma: no cover – bad data
                        logger.warning("Malformed event payload: %s", line)
                elif line.startswith("event: "):
                    # Not needed now – but could be exposed to caller.
                    continue

    # ---------------------------------------------------------------- utils
    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""

        await self._client.aclose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_for_status(resp: httpx.Response) -> None:  # noqa: D401 (imperative mood)
    """Map non-2xx status codes to :class:`OrchestratorError`."""

    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:  # pragma: no cover – network failure
        raise OrchestratorError(str(exc)) from exc
