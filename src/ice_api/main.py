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
from ice_api.api.uploads import router as uploads_router

# keep import grouping minimal; remove unused service imports
from ice_api.errors import add_exception_handlers
from ice_api.redis_client import get_redis
from ice_api.services.component_repo import choose_component_repo
from ice_api.services.component_service import ComponentService

# New startup helpers
from ice_api.startup_utils import (
    print_startup_banner,
    run_alembic_migrations_if_enabled,
    summarise_demo_load,
    timed_import,
    validate_registered_components,
)
from ice_api.ws_gateway import router as ws_router

# Use runtime-wired services (set by orchestrator at startup)
from ice_core import runtime as rt
from ice_core.registry import registry
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

    # Optionally run DB migrations
    await run_alembic_migrations_if_enabled()

    # Ensure first-party tools are provided via plugin manifests; avoid implicit imports

    # ------------------------------------------------------------------
    # Plugin manifests (opt-in starter packs and org components) --------
    # ------------------------------------------------------------------
    try:
        # Load declarative plugins manifests specified via env var. Each entry is a
        # JSON or YAML file containing plugins.v0 components with import paths.
        manifests_env = os.getenv("ICEOS_PLUGIN_MANIFESTS", "").strip()
        if manifests_env:
            import logging as _logging
            import pathlib

            _plog = _logging.getLogger(__name__)
            manifest_paths = [p.strip() for p in manifests_env.split(",") if p.strip()]
            for mp in manifest_paths:
                path = pathlib.Path(mp)
                count = registry.load_plugins(str(path), allow_dynamic=True)
                _plog.info("Loaded %d components from manifest %s", count, path)
            # Fail fast if no tool factories are registered after manifest load
            if not registry.available_tool_factories():
                raise RuntimeError(
                    "No tool factories registered after loading plugin manifests."
                )
    except Exception:  # Log full context for startup diagnostics
        logger.exception("Startup failed during plugin manifest load")
        raise

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
        seconds, mod, import_exc = timed_import(module_path)
        if mod is not None:
            # Call initialize_all if present
            ok = True
            if hasattr(mod, "initialize_all"):
                try:
                    ok = bool(mod.initialize_all("mcp"))  # type: ignore[attr-defined]
                except Exception as init_err:
                    ok = False
                    error_detail = str(init_err)
                else:
                    error_detail = ""
            summarise_demo_load(label, seconds, ok, error_detail)
        else:
            summarise_demo_load(label, seconds, False, str(import_exc))

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

    # Component repository/service
    app.state.component_repo = choose_component_repo(app)  # type: ignore[attr-defined]
    app.state.component_service = ComponentService(app.state.component_repo)  # type: ignore[attr-defined]

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
    # Repo-driven component rehydration (tools + code) ------------------
    # ------------------------------------------------------------------
    # Re-register tool factories from persisted component definitions so they
    # are available immediately after process start. This preserves the repo as
    # the source of truth while keeping runtime UX smooth.
    try:
        if os.getenv("ICEOS_REHYDRATE_COMPONENTS", "1") == "1":
            from typing import Any as _Any

            from ice_core.models.mcp import ComponentDefinition as _CDef

            svc = app.state.component_service  # type: ignore[attr-defined]
            index = await svc.list_index()
            for key in list(index.keys()):
                try:
                    ctype, name = key.split(":", 1)
                except ValueError:
                    continue
                # Support tools, agents, workflows and code.
                if ctype not in ("tool", "agent", "workflow", "code"):
                    continue
                try:
                    rec, _lock = await svc.get(ctype, name)
                except Exception:
                    continue
                if not isinstance(rec, dict):
                    continue
                definition: dict[str, _Any] | None = rec.get("definition")  # type: ignore[assignment]
                if not isinstance(definition, dict):
                    continue
                try:
                    d = _CDef(**definition)
                    # Force runtime registration without altering stored record
                    # Register a callable factory directly when class/factory code is present
                    from ice_core.unified_registry import (
                        has_code_factory as _has_code_factory,
                    )
                    from ice_core.unified_registry import (
                        register_code_factory as _reg_code_factory,
                    )
                    from ice_core.unified_registry import (
                        register_tool_factory_callable as _reg_callable,
                    )

                    try:
                        if d.type == "tool":
                            if d.tool_class_code:
                                ns: dict[str, Any] = {}
                                exec(d.tool_class_code, ns)
                                from ice_core.base_tool import ToolBase

                                klass = None
                                for name, obj in ns.items():
                                    try:
                                        if (
                                            isinstance(obj, type)
                                            and issubclass(obj, ToolBase)
                                            and obj is not ToolBase
                                        ):
                                            klass = obj
                                            break
                                    except Exception:
                                        continue
                                if klass is not None:
                                    from ice_core.protocols.tool import ITool

                                    def _factory(**kwargs: Any) -> ITool:
                                        return cast(ITool, klass(**kwargs))

                                    _reg_callable(d.name, _factory)
                            elif d.tool_factory_code:
                                ns2: dict[str, Any] = {}
                                exec(d.tool_factory_code, ns2)
                                from ice_core.base_tool import ToolBase

                                fac = None
                                for name, obj in ns2.items():
                                    if callable(obj):
                                        try:
                                            inst = obj()
                                            if isinstance(inst, ToolBase):
                                                fac = obj
                                                break
                                        except Exception:
                                            continue
                                if fac is not None:
                                    from ice_core.protocols.tool import ITool as _ITool

                                    _reg_callable(
                                        d.name, cast("Callable[..., _ITool]", fac)
                                    )
                    except Exception:
                        pass
                    # Code components rehydration --------------------------------------
                    try:
                        if d.type == "code":
                            if getattr(d, "code_factory_code", None):
                                if not _has_code_factory(d.name):
                                    import hashlib as _hashlib

                                    ns3: dict[str, Any] = {}
                                    code_str: str = d.code_factory_code or ""
                                    exec(code_str, ns3)
                                    # pick first callable as factory
                                    fac = None
                                    for name, obj in ns3.items():
                                        if callable(obj) and not name.startswith("__"):
                                            fac = obj
                                            break
                                    if fac is not None:
                                        # Create a transient module name based on content hash
                                        import sys as _sys
                                        import types as _types

                                        code_bytes: bytes = (
                                            d.code_factory_code or ""
                                        ).encode()
                                        sha = _hashlib.sha256(code_bytes).hexdigest()[
                                            :12
                                        ]
                                        mod = _types.ModuleType(
                                            f"dynamic_code_{d.name}_{sha}"
                                        )
                                        setattr(mod, fac.__name__, fac)
                                        _sys.modules[mod.__name__] = mod
                                        _reg_code_factory(
                                            d.name, f"{mod.__name__}:{fac.__name__}"
                                        )
                            elif getattr(d, "code_class_code", None):
                                # Optional: support class-based code nodes later
                                pass
                    except Exception:
                        pass
                except Exception:
                    # Non-fatal: leave for JIT fallback during execution
                    pass
    except Exception as _rehydrate_exc:  # pragma: no cover – defensive
        logger.warning("Component rehydration skipped: %s", _rehydrate_exc)

    # ------------------------------------------------------------------
    # Component validation ---------------------------------------------
    # ------------------------------------------------------------------

    validation_summary = validate_registered_components()
    if validation_summary["tool_failures"]:
        raise RuntimeError(
            f"Tool validation failures: {validation_summary['tool_failures']}"
        )

    # Print startup banner last so it appears after early logs ---------
    git_sha = os.getenv("GIT_COMMIT_SHA")
    print_startup_banner(app.version, git_sha)

    # Mark application as ready
    import ice_api.startup_utils as su

    su.READY_FLAG = True
    try:
        logger.info(
            "startupComplete",
            extra={"pid": os.getpid(), "version": app.version},
        )
    except Exception:
        pass

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


# Create FastAPI app with env-driven docs gating
_OPENAPI_PUBLIC = os.getenv("OPENAPI_PUBLIC", "1") == "1"
app = FastAPI(
    title="iceOS API",
    description="AI Workflow Orchestration System",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=("/docs" if _OPENAPI_PUBLIC else None),
    redoc_url=("/redoc" if _OPENAPI_PUBLIC else None),
    openapi_url=("/openapi.json" if _OPENAPI_PUBLIC else None),
)

# OTEL tracing for requests (optional)
if _OTEL_AVAILABLE and OpenTelemetryMiddleware is not None:  # noqa: WPS504
    app.add_middleware(OpenTelemetryMiddleware)
    FastAPIInstrumentor().instrument_app(app)
else:
    logger.warning("OpenTelemetry not installed – tracing disabled")

# Add CORS middleware (env-driven)
_cors_origins = os.getenv("CORS_ORIGINS", "*").strip()
if _cors_origins == "*" or _cors_origins == "":
    _allow_origins = ["*"]
else:
    _allow_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
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


"""Optional drafts feature: gated by ICEOS_ENABLE_DRAFTS=1"""
if os.getenv("ICEOS_ENABLE_DRAFTS", "0") == "1":
    # Include routers
    from ice_api.api import drafts_router as _drafts_router

    app.include_router(_drafts_router)

    # WebSocket endpoint for draft updates ----------------------------------
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
from ice_api.api.storage import router as storage_router
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

app.include_router(
    storage_router,
    prefix="",
    tags=["discovery", "health"],
)

# Secure MCP REST router behind auth
app.include_router(
    mcp_router,
    prefix="/api/mcp",
    tags=["mcp"],
    dependencies=[Depends(require_auth)],
)

from ice_api.ws.executions import router as exec_ws_router

app.include_router(ws_router, prefix="/ws", tags=["websocket"])
app.include_router(exec_ws_router, prefix="/ws", tags=["websocket"])
app.include_router(uploads_router, prefix="", tags=["uploads"])

if os.getenv("ICEOS_ENABLE_METRICS", "0") == "1":
    try:
        from ice_api.metrics import router as metrics_router

        app.include_router(metrics_router)
    except Exception:  # pragma: no cover – optional
        logger.warning(
            "Metrics enabled but prometheus_client not available – skipping /metrics route"
        )

# ------------------------------------------------------------------
# Liveness / readiness routes --------------------------------------
# ------------------------------------------------------------------


@app.get("/healthz", tags=["health"], response_model=Dict[str, str])
async def health_check_legacy() -> Dict[str, str]:  # noqa: D401
    """Health probe – returns 200 when process is running (legacy alias)."""
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


# Version endpoint
@app.get(
    "/api/v1/meta/version", tags=["discovery", "health"], response_model=Dict[str, str]
)
async def version_info() -> Dict[str, str]:  # noqa: D401
    """Return app version and build metadata."""
    return {
        "version": app.version,
        "git_sha": os.getenv("GIT_COMMIT_SHA", "unknown"),
        "build_time": os.getenv("BUILD_TIME", "unknown"),
    }


# Discovery endpoints moved to ice_api.api.discovery


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(cast(Any, app), host="0.0.0.0", port=8000)
