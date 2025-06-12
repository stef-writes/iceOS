"""
FastAPI application entry point
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from ice_sdk.utils.errors import add_exception_handlers
from ice_sdk.context.manager import GraphContextManager
from ice_sdk.utils.logging import setup_logger
from ice_sdk import ToolService

# Setup logging
logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    # Get the project root directory (where .env should be)
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    load_dotenv(dotenv_path=env_path)

    # Create singleton services and attach to app state so they can be injected elsewhere.
    app.state.tool_service = ToolService()  # type: ignore[attr-defined]
    app.state.context_manager = GraphContextManager()  # type: ignore[attr-defined]

    # Load all relevant API keys from environment and make them available if needed by SDKs
    # The actual key used by an LLM call will be the one specified in the Node's LLMConfig.
    # This step ensures that if SDKs implicitly look for env vars, they might be found.

    api_keys_to_load = {
        "OPENAI_API_KEY": None,
        "ANTHROPIC_API_KEY": None,
        "GOOGLE_API_KEY": None,  # For Gemini
        "DEEPSEEK_API_KEY": None,
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

# Include routers
app.include_router(router)


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to iceOS"}
