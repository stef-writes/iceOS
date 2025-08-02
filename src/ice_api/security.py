"""Basic bearer-token auth and budget enforcement stubs."""

from __future__ import annotations

import logging

from fastapi import Header, HTTPException, Request

logger = logging.getLogger(__name__)

DEMO_TOKEN = "demo-token"
BUDGET_LIMIT = 10000  # naive token count limit per execution


def require_auth(authorization: str = Header(...)) -> str:  # noqa: D401
    """FastAPI dependency enforcing bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != DEMO_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
    return token


async def check_budget(request: Request) -> None:  # noqa: D401
    """Pretend BudgetEnforcer – logs if limit exceeded (no real enforcement)."""
    # In real impl we would inspect execution context cost.
    execution_id = request.path_params.get("execution_id")
    if execution_id:
        # TODO: integrate with orchestrator metrics
        logger.debug("Budget check for execution %s", execution_id)