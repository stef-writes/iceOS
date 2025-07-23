"""
FastAPI application entry point
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List, Dict, Any

# ---------------------------------------------------------------------------
# Ensure built-in chain templates register **before** FastAPI app is created
# ---------------------------------------------------------------------------

import importlib

try:
    # Import package (triggers __init__) and explicit module as fallback
    importlib.import_module("ice_sdk.chains")
    importlib.import_module("ice_sdk.chains.inventory_summary_chain")
except Exception:  # pragma: no cover – soft failure in dev envs
    pass

from pydantic import BaseModel

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from ice_api.redis_client import get_redis

# NEW MCP router import
# Service registration (orchestrator runtime) ------------------------------
from ice_orchestrator.services.workflow_service import WorkflowService
from ice_sdk.services import ServiceLocator as _SvcLoc  # avoid name clash later

# Register once at import time so routers can resolve it
if "workflow_service" not in _SvcLoc._services:  # type: ignore[attr-defined]
    _SvcLoc.register("workflow_service", WorkflowService())

# Router imports (can now resolve service)
from ice_api.api.builder import router as builder_router
from ice_api.api.mcp import router as mcp_router
from ice_api.ws_gateway import router as ws_router
from ice_core.utils.logging import setup_logger
from ice_sdk import ToolService
from ice_sdk.context import GraphContextManager

# kb_router removed - focusing on core patterns
from ice_sdk.providers.llm_service import LLMService
from ice_sdk.services import ChainService  # Proper service boundary
from ice_sdk.services import ServiceLocator
from ice_sdk.utils.errors import add_exception_handlers

from importlib import import_module

from ice_sdk.registry.chain import discover_builtin_chains

# Immediately discover chains at import time (tests, CLI usage)
discover_builtin_chains()

# Setup logging
logger = setup_logger()


class _ExecPayload(BaseModel):
    inputs: Dict[str, Any] = {}


class _ChainRunPayload(BaseModel):
    context: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager"""
    # Startup
    # Get the project root directory (where .env should be)
    project_root = Path(__file__).parent.parent.parent

    # Load environment variables from the first existing candidate file.
    # Priority: .env.local (developer-specific) > .env (default) > .env.example (template)
    for candidate in (".env.local", ".env", ".env.example"):
        env_path = project_root / candidate
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            break

    # Create singleton services and attach to app state so they can be injected elsewhere.
    tool_service = ToolService()
    # Expose for tests
    app.state.tool_service = tool_service
    ctx_manager = GraphContextManager()

    # Initialize Redis -----------------------------------------------------
    redis = get_redis()
    try:
        await redis.ping()
    except Exception as exc:
        logger.warning("Redis connection failed: %s", exc)

    app.state.redis = redis  # type: ignore[attr-defined]

    # Register in global ServiceLocator ------------------------------------
    ServiceLocator.register("tool_service", tool_service)
    ServiceLocator.register("context_manager", ctx_manager)
    ServiceLocator.register("llm_service", LLMService())

    # Register built-in tools (best-effort) -----------------------------
    for tool_name in tool_service.available_tools():
        try:
            tool_obj = tool_service.get(tool_name)
            ctx_manager.register_tool(tool_obj)
            logger.info("Tool '%s' registered with context manager", tool_name)
        except Exception as exc:  # pragma: no cover – missing deps etc.
            logger.warning("Tool '%s' could not be registered: %s", tool_name, exc)

    # ------------------------------------------------------------------
    # Ensure built-in chains are imported so their registration side-effects
    # run before blueprints are validated.
    # ------------------------------------------------------------------

    try:
        import importlib
        importlib.import_module("ice_sdk.chains")
        # Explicitly import known built-in chain module in case package __init__ was skipped
        importlib.import_module("ice_sdk.chains.inventory_summary_chain")
    except Exception as exc:  # pragma: no cover – soft failure
        logger.warning("Chain auto-import failed: %s", exc)

    # Auto-discover additional `*.tool.py` modules in the repository ---------
    try:
        tool_service.discover_and_register(project_root)
    except Exception as exc:  # – best-effort discovery
        logger.warning("Tool auto-discovery failed: %s", exc)

    app.state.context_manager = ctx_manager  # type: ignore[attr-defined]

    # Load all relevant API keys from environment and make them available if needed by SDKs
    # The actual key used by an LLM call will be the one specified in the Node's LLMConfig.
    # This step ensures that if SDKs implicitly look for env vars, they might be found.

    # Track presence of optional API keys.  Use explicit ``bool`` values so
    # static type checkers understand what the dictionary will hold.
    api_keys_to_load: dict[str, bool] = {
        "OPENAI_API_KEY": False,
        "ANTHROPIC_API_KEY": False,
        "GOOGLE_API_KEY": False,  # For Gemini
        "DEEPSEEK_API_KEY": False,
    }

    for key_name in api_keys_to_load:
        key_value = os.getenv(key_name)
        if key_value is not None and key_value.strip():  # Check for non-empty string
            os.environ[key_name] = (
                key_value  # Make it available to any SDK that might look for it
            )
            api_keys_to_load[key_name] = True  # Mark as found
            logger.info(f"{key_name} loaded from environment.")
        else:
            api_keys_to_load[key_name] = False
            logger.warning(f"{key_name} not found in environment or .env file.")

    # Example: If you still want to ensure at least one key is present for a default provider
    # if not api_keys_to_load["OPENAI_API_KEY"] and not api_keys_to_load["ANTHROPIC_API_KEY"] etc.:
    #     logger.error("No API keys found for any supported providers. Application might not function correctly.")

    logger.info("Starting up the application...")

    # Register standard exception handlers (must happen *after* app creation).
    add_exception_handlers(app)

    yield

    # Shutdown
    # Add any cleanup code here
    pass


# Create FastAPI app
app = FastAPI(title="iceOS API")

# Expose globally for immediate availability in tests (before lifespan)
tool_service_global = ToolService()
app.state.tool_service = tool_service_global  # type: ignore[attr-defined]
app.state.context_manager = GraphContextManager()  # type: ignore[attr-defined]
app.state.redis = get_redis()  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# CORS – allow any origin for demo/testing so smoke tests pass --------------
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include MCP & builder routers -----------------------------------
app.include_router(mcp_router)
app.include_router(builder_router)
# kb_router removed - focusing on core patterns
app.include_router(ws_router)
# Canvas workflow endpoints
from ice_api.api.workflows import router as workflows_router  # – after FastAPI init

app.include_router(workflows_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Simple welcome endpoint."""
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to iceOS"}


# Add minimal health-check and tools listing endpoints -----------------------


@app.get("/health", tags=["utils"])
async def health_check() -> dict[str, str]:
    """Return simple health status so external monitors can probe the API."""
    return {"status": "ok"}


@app.get("/v1/tools", response_model=List[str], tags=["utils"])
async def list_tools_v1(request: Request) -> List[str]:
    """Return all registered tool names (legacy alias without /api prefix)."""
    tool_service = request.app.state.tool_service  # type: ignore[attr-defined]
    return sorted(tool_service.available_tools())

# ---------------------------------------------------------------------------
# New discovery endpoints ----------------------------------------------------
# ---------------------------------------------------------------------------


from ice_sdk.services.agent_service import AgentService  # placed here to avoid circular import
from ice_sdk.services.unit_service import UnitService
from ice_sdk.services.chain_service import ChainService as _ChainSvc


_agent_service = AgentService()
_unit_service = UnitService()


@app.get("/v1/agents", response_model=List[str], tags=["utils"])
async def list_agents_v1() -> List[str]:
    """Return all registered agent names."""
    return _agent_service.available_agents()


@app.get("/v1/units", response_model=List[str], tags=["utils"])
async def list_units_v1() -> List[str]:
    """Return all registered unit names."""
    return _unit_service.available_units()


@app.get("/v1/chains", response_model=List[str], tags=["utils"])
async def list_chains_v1() -> List[str]:
    """Return all registered reusable chain templates."""
    return _ChainSvc().available_chains()


# ---------------------------------------------------------------------------
# Capability catalog endpoint ------------------------------------------------
# ---------------------------------------------------------------------------


router = APIRouter()


@router.post("/run-chain/{chain_id}")
async def run_chain(chain_id: str, input_data: dict):
    """Generic endpoint that could execute any registered chain"""
    result = await ChainService.execute(chain_id, input_data)
    return {"result": result}


@app.post("/v1/agents/{agent_name}", tags=["execute"])
async def execute_agent_v1(agent_name: str, body: _ExecPayload) -> Any:  # noqa: ANN401 – passthrough
    """Execute *agent* identified by ``agent_name`` with JSON *inputs*."""

    from ice_sdk.services.agent_service import AgentRequest

    result = await _agent_service.execute(
        AgentRequest(agent_name=agent_name, inputs=body.inputs, context={}),
    )
    return {"data": result}


@app.post("/v1/units/{unit_name}", tags=["execute"])
async def execute_unit_v1(unit_name: str, body: _ExecPayload) -> Any:  # noqa: ANN401
    """Execute a *unit* (LLM+Tool composite) by name."""

    from ice_sdk.services.unit_service import UnitRequest

    result = await _unit_service.execute(UnitRequest(unit_name=unit_name, inputs=body.inputs))
    return {"data": result}


@app.post("/v1/chains/{chain_name}", tags=["execute"])
async def run_chain_v1(chain_name: str, body: _ChainRunPayload) -> Any:  # noqa: ANN401
    """Run a reusable chain template registered under *chain_name*."""

    from ice_sdk.services.chain_service import ChainRequest

    chain_svc = _ChainSvc()
    result = await chain_svc.run(ChainRequest(chain_name=chain_name, context=body.context))
    return {"data": result}


# ---------------------------------------------------------------------------
# FastAPI startup hook to load chain templates (workflows)
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def _load_builtin_workflows() -> None:  # noqa: D401
    """Import built-in workflow/chain modules so they self-register."""

    discover_builtin_chains()


# ---------------------------------------------------------------------------
# Workflow (chain) discovery / execution endpoints – alias for /v1/chains
# ---------------------------------------------------------------------------


@app.get("/v1/workflows", response_model=List[str], tags=["utils"])
async def list_workflows_v1() -> List[str]:
    """Return registered reusable workflow templates (same as /v1/chains)."""
    return _ChainSvc().available_chains()


@app.post("/v1/workflows/{workflow_name}", tags=["execute"])
async def run_workflow_v1(workflow_name: str, body: _ChainRunPayload) -> Any:  # noqa: ANN401
    """Run a reusable workflow template by name (alias for /v1/chains/{name})."""

    from ice_sdk.services.chain_service import ChainRequest

    chain_svc = _ChainSvc()
    result = await chain_svc.run(ChainRequest(chain_name=workflow_name, context=body.context))
    return {"data": result}
