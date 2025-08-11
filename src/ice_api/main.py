"""
FastAPI application entry point
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, cast

import structlog
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware

try:
    from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    _OTEL_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover – OTEL optional
    OpenTelemetryMiddleware = None  # type: ignore
    FastAPIInstrumentor = None  # type: ignore
    _OTEL_AVAILABLE = False

from ice_api.api.mcp import router as mcp_router

# keep import grouping minimal; remove unused service imports
from ice_api.errors import add_exception_handlers
from ice_api.redis_client import get_redis

# New startup helpers
from ice_api.startup_utils import (
    print_startup_banner,
    summarise_demo_load,
    timed_import,
    validate_registered_components,
)
from ice_api.ws_gateway import router as ws_router

# Use runtime-wired services (set by orchestrator at startup)
from ice_core import runtime as rt
from ice_core.utils.logging import setup_logger

# Setup logging
logger = setup_logger()

# Quiet overly chatty third-party loggers that spam during tests and dev runs
try:
    import logging as _logging

    for _name in ("httpx", "httpcore"):
        _logging.getLogger(_name).setLevel(_logging.WARNING)
except Exception:  # pragma: no cover – best-effort
    pass

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Sets up services and cleans up resources on shutdown.
    """
    # Initialize services through proper layer interfaces
    import importlib

    initialize_orchestrator = importlib.import_module(
        "ice_orchestrator"
    ).initialize_orchestrator

    # Initialize runtime orchestrator services
    initialize_orchestrator()

    # Ensure first-party generated tools are registered for runtime
    try:
        importlib.import_module("ice_tools.generated")
    except Exception:
        pass

    # ------------------------------------------------------------------
    # Progressive demo loader with timing --------------------------------
    # ------------------------------------------------------------------

    import sys

    project_root = Path(__file__).parent.parent.parent
    use_cases_path = project_root / "use_cases"

    if str(use_cases_path) not in sys.path:
        sys.path.insert(0, str(use_cases_path))

    env_packs = os.getenv("ICEOS_OPTIONAL_PACKS")
    if env_packs:
        raw_paths = [p.strip() for p in env_packs.split(",") if p.strip()]
        demo_modules = [
            (module_path.split(".")[-1], module_path) for module_path in raw_paths
        ]
    else:
        demo_modules = []  # No default demos – avoid noisy import errors

    for label, module_path in demo_modules:
        seconds, mod, exc = timed_import(module_path)
        if mod is not None:
            # Call initialize_all if present
            ok = True
            if hasattr(mod, "initialize_all"):
                try:
                    ok = bool(mod.initialize_all("mcp"))  # type: ignore[attr-defined]
                except Exception as ie:
                    ok = False
                    exc = ie
            summarise_demo_load(label, seconds, ok, "" if ok else str(exc))
        else:
            summarise_demo_load(label, seconds, False, str(exc))

    # Prefer runtime-wired context manager
    app.state.context_manager = rt.context_manager  # type: ignore[attr-defined]

    # Register workflow execution service for API execution endpoints without
    # top-level import. Use runtime-wired service if present, else lazy import.
    try:
        if getattr(rt, "workflow_execution_service", None) is None:
            from importlib import import_module

            wes_cls = getattr(
                import_module("ice_orchestrator.services.workflow_execution_service"),
                "WorkflowExecutionService",
            )
            rt.workflow_execution_service = wes_cls()
    except Exception as reg_exc:  # pragma: no cover – defensive
        logger.warning("Failed to prepare workflow_execution_service: %s", reg_exc)

    # Initialize tool service to bridge unified registry to API endpoints
    from ice_core.services.tool_service import ToolService

    app.state.tool_service = ToolService()  # type: ignore[attr-defined]

    # In-memory stores for blueprints and execution results (demo profile)
    app.state.blueprints = {}
    app.state.executions = {}

    # Load API keys from environment
    api_keys_to_load: dict[str, bool] = {
        "OPENAI_API_KEY": False,
        "ANTHROPIC_API_KEY": False,
        "GOOGLE_API_KEY": False,
        "DEEPSEEK_API_KEY": False,
    }

    for key_name in api_keys_to_load:
        has_key = os.getenv(key_name) is not None
        api_keys_to_load[key_name] = has_key
        if has_key:
            logger.info(f"Found {key_name} in environment")
        else:
            logger.debug(f"{key_name} not found in environment")

    # Initialize Redis connection, with zero-setup fallback to in-memory stub
    try:
        redis = get_redis()
        await redis.ping()  # type: ignore[misc]
        logger.info("Redis connection established")
    except Exception as exc:  # pragma: no cover – fallback path
        logger.warning("Redis unavailable (%s) – falling back to in-memory stub", exc)
        import os as _os

        _os.environ["USE_FAKE_REDIS"] = "1"
        # Recreate client as stub
        redis = get_redis()
        try:
            await redis.ping()  # type: ignore[misc]
        except Exception:
            # Stub ping always succeeds; ignore
            pass

    # ------------------------------------------------------------------
    # Component validation ---------------------------------------------
    # ------------------------------------------------------------------

    validation_summary = validate_registered_components()
    if validation_summary["tool_failures"]:
        logger.warning(
            "⚠️  Some tools failed validation: %s", validation_summary["tool_failures"]
        )

    # Print startup banner last so it appears after early logs ---------
    git_sha = os.getenv("GIT_COMMIT_SHA")
    print_startup_banner(app.version, git_sha)

    # Mark application as ready
    import ice_api.startup_utils as su

    su.READY_FLAG = True

    yield

    # Cleanup on shutdown
    logger.info("Application shutting down")
    try:
        if hasattr(redis, "aclose"):
            await redis.aclose()  # type: ignore[attr-defined]
        elif hasattr(redis, "close"):
            await redis.close()  # type: ignore[attr-defined]
    except Exception as exc:
        logger.warning("Error while closing Redis connection: %s", exc)


# Create FastAPI app
app = FastAPI(
    title="iceOS API",
    description="AI Workflow Orchestration System",
    version="0.1.0",
    lifespan=lifespan,
)

# OTEL tracing for requests (optional)
if _OTEL_AVAILABLE and OpenTelemetryMiddleware is not None:  # noqa: WPS504
    app.add_middleware(OpenTelemetryMiddleware)
    FastAPIInstrumentor().instrument_app(app)
else:
    logger.warning("OpenTelemetry not installed – tracing disabled")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handlers
add_exception_handlers(app)


# Add request context for structured logging
@app.middleware("http")
async def add_request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    structlog.contextvars.bind_contextvars(path=request.url.path, method=request.method)
    response = await call_next(request)
    structlog.contextvars.clear_contextvars()
    return response


# Include routers
from ice_api.api import drafts_router as _drafts_router

app.include_router(_drafts_router)

# WebSocket endpoint for draft updates --------------------------------------
from ice_api.ws import draft_ws as _draft_ws


@app.websocket("/ws/drafts/{session_id}")
async def draft_updates(ws: WebSocket, session_id: str) -> None:
    await _draft_ws.register(session_id, ws)
    try:
        while True:
            await ws.receive_text()  # keep connection alive (client pings)
    except Exception:
        pass
    finally:
        await _draft_ws.unregister(session_id, ws)


from ice_api.api.blueprints import router as blueprint_router  # ensure module import
from ice_api.api.catalog import router as catalog_router
from ice_api.api.discovery import router as discovery_router
from ice_api.api.executions import router as execution_router
from ice_api.api.node_details import router as node_details_router
from ice_api.api.registry_health import router as registry_health_router
from ice_api.security import require_auth

app.include_router(
    blueprint_router,
    prefix="",
    tags=["blueprints"],
    dependencies=[Depends(require_auth)],
)
app.include_router(
    execution_router,
    prefix="",
    tags=["executions"],
    dependencies=[Depends(require_auth)],
)

# Discovery endpoints (moved out of main)
app.include_router(
    discovery_router,
    prefix="",
    tags=["discovery"],
)

app.include_router(
    catalog_router,
    prefix="",
    tags=["catalog"],
)

app.include_router(
    node_details_router,
    prefix="",
    tags=["catalog", "schemas"],
)

app.include_router(
    registry_health_router,
    prefix="",
    tags=["discovery", "health"],
)

# Secure MCP REST router behind auth
app.include_router(
    mcp_router,
    prefix="/api/v1/mcp",
    tags=["mcp"],
    dependencies=[Depends(require_auth)],
)

from ice_api.ws.executions import router as exec_ws_router

app.include_router(ws_router, prefix="/ws", tags=["websocket"])
app.include_router(exec_ws_router, prefix="/ws", tags=["websocket"])

from ice_api.metrics import router as metrics_router

app.include_router(metrics_router)

# ------------------------------------------------------------------
# Liveness / readiness routes --------------------------------------
# ------------------------------------------------------------------


@app.get("/livez", tags=["health"], response_model=Dict[str, str])
async def live_check() -> Dict[str, str]:  # noqa: D401
    """Liveness probe – always returns 200 when the server process is running."""
    return {"status": "live"}


# ------------------------------------------------------------------


@app.get("/readyz", tags=["health"], response_model=Dict[str, str])
async def ready_check() -> Dict[str, str]:
    """Readiness probe – returns 200 only after full startup."""
    import ice_api.startup_utils as su

    return {"status": "ready" if su.READY_FLAG else "starting"}


# Add real MCP JSON-RPC 2.0 endpoint
from ice_api.api.mcp_jsonrpc import router as mcp_jsonrpc_router

# Secure MCP JSON-RPC endpoint behind auth as well
app.include_router(
    mcp_jsonrpc_router,
    prefix="/api/mcp",
    tags=["mcp-jsonrpc"],
    dependencies=[Depends(require_auth)],
)


# Root endpoint
@app.get("/", response_model=Dict[str, str])
async def root() -> Dict[str, str]:
    """Root endpoint returning API info."""
    return {
        "message": "iceOS API",
        "version": "0.1.0",
        "docs": "/docs",
    }


# Health check
@app.get("/health", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    try:
        redis = get_redis()
        await redis.ping()  # type: ignore[misc]
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


# Discovery endpoints moved to ice_api.api.discovery


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(cast(Any, app), host="0.0.0.0", port=8000)
