import time
from typing import Any, Dict, Tuple

from fastapi import Depends, HTTPException, Request

from ice_api.security import require_auth
from ice_core.services.tool_service import ToolService


def get_tool_service(request: Request) -> ToolService:
    """Return the application-wide ToolService stored in `app.state`."""
    return request.app.state.tool_service  # type: ignore[attr-defined,no-any-return]

def get_context_manager(request: Request) -> Any:
    """Return the shared context manager stored in `app.state`.
    
    Note: Using Any type to avoid layer boundary violation.
    The actual type is GraphContextManager from ice_orchestrator.
    """
    return request.app.state.context_manager  # type: ignore[attr-defined,no-any-return]

# ---------------------------------------------------------------------------
# Simple in-process rate limiter (shared across routes) ----------------------
# ---------------------------------------------------------------------------
_RATE_LIMIT: Dict[Tuple[str, str], list[float]] = {}
_RATE_WINDOW = 10.0  # seconds
_RATE_MAX = 5  # requests per window

def rate_limit(request: Request, token: str = Depends(require_auth)) -> None:  # noqa: D401
    """Basic token+path bucket rate limiter (dev profile)."""
    now = time.time()
    key = (token, request.url.path)
    bucket = _RATE_LIMIT.setdefault(key, [])
    # Purge old timestamps
    _RATE_LIMIT[key] = [t for t in bucket if now - t < _RATE_WINDOW]
    if len(_RATE_LIMIT[key]) >= _RATE_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _RATE_LIMIT[key].append(now)
