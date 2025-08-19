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

    # -------------------------------------------------------- MCP components
    async def scaffold_component(
        self,
        component_type: str,
        name: str,
        *,
        template: str | None = None,
    ) -> Mapping[str, Any]:
        """Request scaffold code for a new component.

        Parameters
        ----------
        component_type : str
            One of "tool", "agent", or "workflow".
        name : str
            Public name of the component.
        template : str | None
            Optional template variant.

        Returns
        -------
        Mapping[str, Any]
            Response containing scaffold code fields and notes.

        Example
        -------
        >>> await client.scaffold_component("tool", "csv_loader")
        """

        url = f"{self._API_PREFIX}/components/scaffold"
        payload: MutableMapping[str, Any] = {"type": component_type, "name": name}
        if template is not None:
            payload["template"] = template
        resp = await self._client.post(url, json=payload)
        _raise_for_status(resp)
        data: Any = resp.json()
        assert isinstance(data, dict)
        return data

    async def register_component(
        self, definition: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Validate then persist and register a component definition.

        Returns a payload including `version_lock` on success.
        """

        url = f"{self._API_PREFIX}/components/register"
        resp = await self._client.post(url, json=dict(definition))
        _raise_for_status(resp)
        data: Any = resp.json()
        assert isinstance(data, dict)
        return data

    async def list_components(self) -> Mapping[str, Any]:
        """List stored components and currently registered factories."""

        url = f"{self._API_PREFIX}/components"
        resp = await self._client.get(url)
        _raise_for_status(resp)
        data: Any = resp.json()
        assert isinstance(data, dict)
        return data

    async def get_component(
        self, component_type: str, name: str
    ) -> tuple[Mapping[str, Any], Optional[str]]:
        """Fetch a stored component and its current version lock (if any)."""

        url = f"{self._API_PREFIX}/components/{component_type}/{name}"
        resp = await self._client.get(url)
        _raise_for_status(resp)
        lock = resp.headers.get("X-Version-Lock")
        obj: Any = resp.json()
        assert isinstance(obj, dict)
        return obj, lock

    async def update_component(
        self,
        component_type: str,
        name: str,
        definition: Mapping[str, Any],
        *,
        version_lock: str,
    ) -> str:
        """Update a stored component using optimistic concurrency.

        Returns the new `version_lock`.
        """

        url = f"{self._API_PREFIX}/components/{component_type}/{name}"
        headers = {"X-Version-Lock": version_lock}
        resp = await self._client.put(url, json=dict(definition), headers=headers)
        _raise_for_status(resp)
        data = resp.json()
        return str(data.get("version_lock", ""))

    async def delete_component(self, component_type: str, name: str) -> None:
        """Delete a stored component definition."""

        url = f"{self._API_PREFIX}/components/{component_type}/{name}"
        resp = await self._client.delete(url)
        _raise_for_status(resp)

    async def compose_agent(
        self,
        name: str,
        *,
        system_prompt: str | None = None,
        tools: list[str] | None = None,
        llm_config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Compose and register a simple agent definition (not BYOK)."""

        url = f"{self._API_PREFIX}/agents/compose"
        payload: MutableMapping[str, Any] = {
            "name": name,
            "system_prompt": system_prompt,
            "tools": list(tools or []),
            "llm_config": dict(llm_config or {}),
        }
        resp = await self._client.post(url, json=payload)
        _raise_for_status(resp)
        data: Any = resp.json()
        assert isinstance(data, dict)
        return data

    # ---------------------------------------------- Partial blueprints (MCP)
    async def create_partial_blueprint(
        self, initial_node: Mapping[str, Any] | None = None
    ) -> Mapping[str, Any]:
        """Create a new partial blueprint; returns the partial blueprint JSON."""

        url = f"{self._API_PREFIX}/blueprints/partial"
        # Body is optional per API; include only when provided
        json_body = initial_node if initial_node is not None else None
        resp = await self._client.post(url, json=json_body)
        _raise_for_status(resp)
        data: Any = resp.json()
        assert isinstance(data, dict)
        return data

    async def get_partial_blueprint(
        self, blueprint_id: str
    ) -> tuple[Mapping[str, Any], Optional[str]]:
        """Fetch partial blueprint JSON and current version lock header."""

        url = f"{self._API_PREFIX}/blueprints/partial/{blueprint_id}"
        resp = await self._client.get(url)
        _raise_for_status(resp)
        lock = resp.headers.get("X-Version-Lock")
        return resp.json(), lock

    async def update_partial_blueprint(
        self,
        blueprint_id: str,
        update: Mapping[str, Any],
        *,
        version_lock: str,
    ) -> Mapping[str, Any]:
        """Apply an incremental update; requires X-Version-Lock."""

        url = f"{self._API_PREFIX}/blueprints/partial/{blueprint_id}"
        headers = {"X-Version-Lock": version_lock}
        resp = await self._client.put(url, json=dict(update), headers=headers)
        _raise_for_status(resp)
        data: Any = resp.json()
        assert isinstance(data, dict)
        return data

    async def finalize_partial_blueprint(
        self, blueprint_id: str, *, version_lock: str
    ) -> Mapping[str, Any]:
        """Finalize a partial blueprint to an executable blueprint; returns ack."""

        url = f"{self._API_PREFIX}/blueprints/partial/{blueprint_id}/finalize"
        headers = {"X-Version-Lock": version_lock}
        resp = await self._client.post(url, headers=headers)
        _raise_for_status(resp)
        data: Any = resp.json()
        assert isinstance(data, dict)
        return data

    async def suggest_partial(
        self,
        blueprint_id: str,
        *,
        top_k: int = 5,
        allowed_types: list[str] | None = None,
        commit: bool = False,
        version_lock: str | None = None,
    ) -> Mapping[str, Any]:
        """Request suggestions for next nodes; commit path requires X-Version-Lock."""

        url = f"{self._API_PREFIX}/blueprints/partial/{blueprint_id}/suggest"
        body: MutableMapping[str, Any] = {"top_k": top_k, "commit": commit}
        if allowed_types is not None:
            body["allowed_types"] = list(allowed_types)
        headers: MutableMapping[str, str] = {}
        if commit and version_lock is not None:
            headers["X-Version-Lock"] = version_lock
        resp = await self._client.post(url, json=body, headers=headers or None)
        _raise_for_status(resp)
        data: Any = resp.json()
        assert isinstance(data, dict)
        return data

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
            "blueprint_id": bp_id,
            "inputs": dict(inputs or {}),
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

    # ---------------------------------------------- Studio convenience APIs
    async def run_and_wait(
        self,
        *,
        blueprint: Blueprint | Mapping[str, Any] | None = None,
        blueprint_id: str | None = None,
        max_parallel: int = 5,
    ) -> RunResult:
        """Submit a run via MCP and wait for completion.

        Parameters
        ----------
        blueprint : Blueprint | Mapping[str, Any] | None
            Inline blueprint definition to run (takes precedence over blueprint_id).
        blueprint_id : str | None
            ID of a blueprint registered on the server.
        max_parallel : int
            Concurrency hint for the orchestrator.

        Returns
        -------
        RunResult

        Example
        -------
        >>> result = await client.run_and_wait(blueprint_id="bp_abc")
        >>> assert result.success
        """

        ack = await self.submit_blueprint(
            blueprint, blueprint_id=blueprint_id, max_parallel=max_parallel
        )
        return await self.wait_for_completion(ack.run_id)

    async def run_and_stream(
        self,
        *,
        blueprint: Blueprint | Mapping[str, Any] | None = None,
        blueprint_id: str | None = None,
        max_parallel: int = 5,
    ) -> AsyncIterator[dict[str, Any]]:
        """Submit a run via MCP and stream SSE events until completion.

        Yields
        ------
        dict[str, Any]
            Event payloads as emitted by the server (SSE).

        Example
        -------
        >>> async for evt in client.run_and_stream(blueprint_id="bp_abc"):
        ...     print(evt)
        """

        ack = await self.submit_blueprint(
            blueprint, blueprint_id=blueprint_id, max_parallel=max_parallel
        )
        async for evt in self.stream_events(ack.run_id):
            yield evt

    # -------------------------------------------------------------- chat API
    async def chat_turn(
        self,
        agent_name: str,
        session_id: str,
        user_message: str,
        *,
        reset: bool = False,
    ) -> Mapping[str, Any]:
        """Send one chat turn to an agent and get assistant reply.

        Returns a dict containing session_id, agent_name, assistant_message.
        """

        url = f"{self._API_PREFIX}/chat/{agent_name}"
        payload = {
            "session_id": session_id,
            "user_message": user_message,
            "reset": reset,
        }
        resp = await self._client.post(url, json=payload)
        _raise_for_status(resp)
        data: Any = resp.json()
        assert isinstance(data, dict)
        return data

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
