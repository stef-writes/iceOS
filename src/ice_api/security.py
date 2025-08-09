"""Basic bearer-token auth and budget enforcement stubs.

Auth token is sourced from environment variable ``ICE_API_TOKEN`` with a
development default of ``dev-token``.
"""

from __future__ import annotations

import logging
import os

from fastapi import Header, HTTPException, Request

logger = logging.getLogger(__name__)


def _expected_token() -> str:
    """Return the configured API bearer token (dev default)."""
    return os.getenv("ICE_API_TOKEN", "dev-token").strip()


def require_auth(authorization: str = Header(...)) -> str:  # noqa: D401
    """FastAPI dependency enforcing bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != _expected_token():
        raise HTTPException(status_code=403, detail="Invalid token")
    return token


async def check_budget(request: Request) -> None:  # noqa: D401
    """Pretend BudgetEnforcer – logs if limit exceeded (no real enforcement)."""
    # In real impl we would inspect execution context cost.
    execution_id = request.path_params.get("execution_id")
    if execution_id:
        # TODO: integrate with orchestrator metrics
        logger.debug("Budget check for execution %s", execution_id)


# ---------------------------------------------------------------------------
# Component access policy (tools/agents) -------------------------------------
# ---------------------------------------------------------------------------


def _csv_env(name: str) -> set[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return set()
    return {p.strip() for p in raw.split(",") if p.strip()}


_ALLOWED_TOOLS = _csv_env("ICE_ALLOWED_TOOLS")
_DENIED_TOOLS = _csv_env("ICE_DENIED_TOOLS")
_ALLOWED_AGENTS = _csv_env("ICE_ALLOWED_AGENTS")
_DENIED_AGENTS = _csv_env("ICE_DENIED_AGENTS")


def is_tool_allowed(name: str) -> bool:
    """Return True if the tool name passes the policy.

    Policy: if allowed-set is non-empty, only those are permitted. Then apply
    explicit deny list. Defaults to allow-all when both sets empty.
    """

    if _ALLOWED_TOOLS and name not in _ALLOWED_TOOLS:
        return False
    if name in _DENIED_TOOLS:
        return False
    return True


def is_agent_allowed(name: str) -> bool:
    if _ALLOWED_AGENTS and name not in _ALLOWED_AGENTS:
        return False
    if name in _DENIED_AGENTS:
        return False
    return True
