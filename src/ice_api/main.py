"""
FastAPI application entry point
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from ice_api.redis_client import get_redis
from ice_api.api.mcp import router as mcp_router
from ice_api.dependencies import get_tool_service
from ice_api.api.direct_execution import router as direct_router
from ice_api.ws_gateway import router as ws_router
from ice_core.utils.logging import setup_logger
from ice_sdk import ToolService
# Note: API layer uses ServiceLocator for orchestrator services
from ice_sdk.services import ServiceLocator
from ice_api.errors import add_exception_handlers

# Setup logging
logger = setup_logger()

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.
    
    Sets up services and cleans up resources on shutdown.
    """
    # Initialize services through proper layer interfaces
    from ice_sdk.services.initialization import initialize_sdk
    from ice_orchestrator import initialize_orchestrator
    
    # Initialize layers in order
    initialize_sdk()
    initialize_orchestrator()

    # Load custom demo components if available
    try:
        import sys
        import os
        from pathlib import Path
        
        # Add use-cases to path if FB Marketplace demo exists
        project_root = Path(__file__).parent.parent.parent
        use_cases_path = project_root / "use-cases"
        fb_marketplace_path = use_cases_path / "RivaRidge" / "FB_Marketplace_Seller"
        
        if fb_marketplace_path.exists():
            logger.info("Loading FB Marketplace Seller demo components...")
            if str(use_cases_path) not in sys.path:
                sys.path.insert(0, str(use_cases_path))
            
            # Import and initialize FB Marketplace Seller components
            from RivaRidge.FB_Marketplace_Seller.initialization import initialize_all
            success = initialize_all("mcp")
            
            if success:
                logger.info("✅ FB Marketplace Seller components loaded successfully")
            else:
                logger.warning("⚠️ FB Marketplace Seller components failed to load")
    except Exception as e:
        logger.info(f"FB Marketplace demo not available: {e}")

    app.state.context_manager = ServiceLocator.get("context_manager")  # type: ignore[attr-defined]
    
    # Initialize tool service to bridge unified registry to API endpoints
    from ice_sdk.tools.service import ToolService
    app.state.tool_service = ToolService()  # type: ignore[attr-defined]

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

    # Initialize Redis connection
    redis = await get_redis()
    await redis.ping()
    logger.info("Redis connection established")

    yield

    # Cleanup on shutdown
    logger.info("Application shutting down")

# Create FastAPI app
app = FastAPI(
    title="iceOS API",
    description="AI Workflow Orchestration System",
    version="0.1.0",
    lifespan=lifespan,
)

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

# Include routers
app.include_router(mcp_router, prefix="/api/v1/mcp", tags=["mcp"])
app.include_router(direct_router, tags=["direct"])
app.include_router(ws_router, prefix="/ws", tags=["websocket"])

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
        redis = await get_redis()
        await redis.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

# Discovery endpoints
@app.get("/api/v1/tools", response_model=List[str], tags=["discovery"])
async def list_tools(tool_service = Depends(get_tool_service)) -> List[str]:
    """Return all registered tool names."""
    return tool_service.available_tools()

@app.get("/v1/agents", response_model=List[str], tags=["discovery"])
async def list_agents() -> List[str]:
    """Return all registered agent names."""
    from ice_core.unified_registry import registry
    return list(registry._agents.keys())

@app.get("/v1/workflows", response_model=List[str], tags=["discovery"]) 
async def list_workflows() -> List[str]:
    """Return all registered workflow names."""
    from ice_core.unified_registry import registry
    from ice_core.models import NodeType
    return [name for name, _ in registry.available_instances(NodeType.WORKFLOW)]

@app.get("/v1/chains", response_model=List[str], tags=["discovery"])
async def list_chains() -> List[str]:
    """Return all registered chain names."""
    from ice_core.unified_registry import global_chain_registry
    return [name for name, _ in global_chain_registry.available()]

@app.get("/api/v1/executors", response_model=Dict[str, str], tags=["discovery"])
async def list_executors() -> Dict[str, str]:
    """Return all registered executors."""
    from ice_core.unified_registry import registry
    return {k: v.__name__ for k, v in registry._executors.items()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
