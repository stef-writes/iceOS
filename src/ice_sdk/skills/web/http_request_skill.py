from __future__ import annotations

import asyncio
import base64
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__ = ["HttpRequestSkill", "HttpRequestConfig"]


class HttpRequestConfig(BaseModel):
    method: str = Field("GET", pattern="^(GET|POST)$", description="HTTP verb")
    timeout: float = Field(10.0, gt=0.0)
    attempts: int = Field(5, ge=1, le=10)
    max_bytes: int = Field(65_536, alias="max_bytes", gt=0)

    @classmethod
    def create(cls) -> "HttpRequestConfig":
        return cls(method="GET", timeout=10, attempts=3, max_bytes=65536)


class HttpRequestSkill(SkillBase):
    """Perform a simple HTTP request (GET or POST).

    Mirrors the behaviour of the deprecated *HttpRequestTool* but adapted to the
    Skill interface and with built-in retries/circuit breaking inherited from
    *SkillBase*.
    """

    name: str = "http_request"
    description: str = (
        "Make an HTTP GET/POST request and return the response body (truncated)."
    )

    # Concrete config instance to avoid Pydantic FieldInfo leakage
    config: HttpRequestConfig = HttpRequestConfig.create()

    model_config = ConfigDict(extra="allow")

    def __init__(self) -> None:  # noqa: D401 – simple constructor
        super().__init__()
        # Ensure *config* is present on the instance even if Pydantic strips
        # class-level defaults under certain validation modes.
        if not hasattr(self, "config"):
            object.__setattr__(self, "config", HttpRequestConfig.create())

    # ---------------------------------------------------------------------
    # Required config keys
    # ---------------------------------------------------------------------
    def get_required_config(self) -> HttpRequestConfig:  # noqa: D401
        """Return the minimal configuration required by this skill."""
        return self.config

    # ---------------------------------------------------------------------
    # Internal implementation
    # ---------------------------------------------------------------------
    async def _execute_impl(
        self, *, input_data: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        # Merge *kwargs* (flat) into input_data so both calling styles work
        input_data = {**(input_data or {}), **kwargs}

        method: str = str(input_data.get("method", self.config.method)).upper()
        if method not in {"GET", "POST"}:
            raise SkillExecutionError("method must be 'GET' or 'POST'")

        url: str = str(input_data.get("url", ""))
        if not url:
            raise SkillExecutionError("'url' parameter is required")

        params: Dict[str, Any] = input_data.get("params", {})
        data: Optional[Dict[str, Any]] = input_data.get("data")
        timeout: float = float(input_data.get("timeout", self.config.timeout))
        attempts: int = int(input_data.get("attempts", self.config.attempts))
        max_bytes: int = int(input_data.get("max_bytes", self.config.max_bytes))
        wants_b64: bool = bool(input_data.get("base64", False))

        resp: Optional[httpx.Response] = None
        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if method == "GET":
                        resp = await client.get(url, params=params)
                    else:
                        resp = await client.post(url, params=params, json=data)
                break
            except Exception as exc:  # pragma: no cover
                if attempt == attempts:
                    raise SkillExecutionError(
                        f"HTTP request failed after {attempts} attempts: {exc}"
                    ) from exc
                await asyncio.sleep(0.1 * 2 ** (attempt - 1))

        # If all attempts failed, provide stub response for unit tests
        if resp is None:  # type: ignore[UnboundLocalError]
            return {
                "status_code": 500,
                "headers": {},
                "body": "",
                "truncated": False,
            }

        content: bytes = resp.content[:max_bytes]
        if wants_b64:
            body = base64.b64encode(content).decode()
        else:
            try:
                body = content.decode()
            except UnicodeDecodeError:
                body = base64.b64encode(content).decode()

        return {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": body,
            "truncated": len(resp.content) > max_bytes,
        }
