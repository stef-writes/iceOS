"""
FastAPI application entry point
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.builder import router as builder_router
from app.api.routes import router
from ice_sdk import ToolService
from ice_sdk.context import GraphContextManager
from ice_sdk.extensions.kb_router import router as kb_router
from ice_sdk.providers.llm_service import LLMService
from ice_sdk.services import ServiceLocator
from ice_sdk.utils.errors import add_exception_handlers
from ice_sdk.utils.logging import setup_logger

# Setup logging
logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    ctx_manager = GraphContextManager()

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

    # Auto-discover additional `*.tool.py` modules in the repository ---------
    try:
        tool_service.discover_and_register(project_root)
    except Exception as exc:  # noqa: BLE001 – best-effort discovery
        logger.warning("Tool auto-discovery failed: %s", exc)

    app.state.tool_service = tool_service  # type: ignore[attr-defined]
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
app = FastAPI(
    title="iceOS",
    description="iceOS: Flexible, plugin-driven AI workflow and agent orchestration platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include core & builder routers -----------------------------------
app.include_router(router)
app.include_router(builder_router)
app.include_router(kb_router)


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to iceOS"}


# Add minimal health-check and tools listing endpoints -----------------------


@app.get("/health", tags=["utils"])
async def health_check():  # noqa: D401
    """Return simple health status so external monitors can probe the API."""
    return {"status": "ok"}


@app.get("/v1/tools", response_model=List[str], tags=["utils"])
async def list_tools_v1(request: Request):  # noqa: D401
    """Return all registered tool names (legacy alias without /api prefix)."""
    tool_service = request.app.state.tool_service  # type: ignore[attr-defined]
    return sorted(tool_service.available_tools())
