"""
API routes for the workflow engine
"""

# pyright: reportCallIssue=false, reportArgumentType=false, reportAttributeAccessIssue=false

# Removed explicit built-in tool imports, ToolService already loads defaults
import traceback
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ValidationError

# Dependency injection functions from app.dependencies
from app.dependencies import get_context_manager, get_tool_service
from ice_orchestrator import ScriptChain
from ice_sdk import ToolService
from ice_sdk.agents.agent_node import AgentNode
from ice_sdk.models.agent_models import AgentConfig, ModelSettings
from ice_sdk.models.node_models import (
    ChainExecutionResult,
    NodeConfig,
    NodeExecutionResult,
    NodeMetadata,
)
from ice_sdk.utils.logging import logger

router = APIRouter(prefix="/api/v1")


class NodeRequest(BaseModel):
    """Request model for node operations"""

    config: NodeConfig
    context: Optional[Dict[str, Any]] = None


class WorkflowRequest(BaseModel):
    """Workflow execution request."""
    nodes: List[NodeConfig]
    name: Optional[str] = None
    max_parallel: int = 5
    persist_intermediate_outputs: bool = True
    initial_context: Optional[Dict[str, Any]] = None


@router.post("/nodes/text-generation", response_model=NodeExecutionResult)
async def create_text_generation_node(
    request: NodeRequest,
    tool_service: ToolService = Depends(get_tool_service),
    context_manager=Depends(get_context_manager),
):
    """Create and execute a text generation node"""
    try:
        # Create agent config from node config
        agent_config = AgentConfig(
            id=request.config.id,
            name=request.config.name,
            description=request.config.description,
            model_settings=ModelSettings(
                provider=request.config.llm_config.provider,
                model=request.config.llm_config.model,
                temperature=request.config.llm_config.temperature,
                max_tokens=request.config.llm_config.max_tokens,
            ),
            tools=request.config.tools if hasattr(request.config, 'tools') else [],
        )

        # Create and execute agent
        agent = AgentNode(agent_config, context_manager, tool_service)
        result = await agent.execute(request.context or {})

        # If execution was successful, update the context manager with its output
        if result.success and result.output:
            context_manager.update_context(request.config.id, result.output)

        return result
    except ValidationError as e:
        return NodeExecutionResult(
            success=False,
            error=str(e),
            metadata=NodeMetadata(
                node_id=request.config.id,
                node_type=request.config.type,
                error_type="validation_error",
            ),
        )
    except ValueError as e:
        return NodeExecutionResult(
            success=False,
            error=str(e),
            metadata=NodeMetadata(
                node_id=request.config.id,
                node_type=request.config.type,
                error_type="value_error",
            ),
        )
    except Exception as e:
        logger.error(f"Error in text generation node: {str(e)}")
        return NodeExecutionResult(
            success=False,
            error="Internal server error",
            metadata=NodeMetadata(
                node_id=request.config.id,
                node_type=request.config.type,
                error_type="internal_error",
            ),
        )


@router.post("/workflow")
async def execute_workflow(request: WorkflowRequest) -> Dict[str, Any]:
    """Execute a workflow."""
    try:
        chain = ScriptChain(
            nodes=request.nodes,
            name=request.name,
            max_parallel=request.max_parallel,
            persist_intermediate_outputs=request.persist_intermediate_outputs,
            initial_context=request.initial_context,
        )
        result = await chain.execute()
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{node_id}/context")
async def get_node_context(
    node_id: str,
    limit: int | None = Query(
        None,
        ge=1,
        description="Max number of keys to return (dicts will be truncated).",
    ),
    after: str | None = Query(
        None, description="Pagination cursor – last key from previous page."
    ),
    context_manager=Depends(get_context_manager),
):
    """Get context for a specific node"""
    try:
        context = context_manager.get_context(node_id)
        if not context:
            raise HTTPException(
                status_code=404, detail=f"Context not found for node {node_id}"
            )
        if isinstance(context, dict) and limit is not None:
            keys = sorted(context.keys())
            if after and after in keys:
                start_index = keys.index(after) + 1
            else:
                start_index = 0
            slice_keys = keys[start_index : start_index + limit]
            context = {k: context[k] for k in slice_keys}
        return context
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting node context: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/nodes/{node_id}/context")
async def clear_node_context(
    node_id: str, context_manager=Depends(get_context_manager)
):
    """Clear context for a specific node"""
    logger.info(f"API HANDLER: clear_node_context CALLED for node_id: {node_id}")
    try:
        # Attempt to clear the context. The manager's clear_context
        # should handle cases where the node_id doesn't exist gracefully.
        context_manager.clear_context(node_id)
        logger.info(f"API HANDLER: clear_node_context SUCCESS for node_id: {node_id}")
        return {"message": f"Context cleared for node {node_id}"}
    except Exception as e:
        logger.error(
            f"API HANDLER: Error clearing node context for {node_id}: {str(e)}"
        )
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/execute/node", response_model=NodeExecutionResult)
async def execute_node(
    request: NodeRequest,
    tool_service: ToolService = Depends(get_tool_service),
    context_manager=Depends(get_context_manager),
):
    """Alias for creating/executing a single node (generic)."""
    return await create_text_generation_node(request, tool_service, context_manager)


@router.post("/execute/chain", response_model=ChainExecutionResult)
async def execute_chain_alias(
    request: WorkflowRequest,
    tool_service: ToolService = Depends(get_tool_service),
    context_manager=Depends(get_context_manager),
):
    """Alias for executing a chain (generic path)."""
    return await execute_workflow(request)


@router.get("/tools", response_model=List[str])
async def list_tools(
    tool_service: ToolService = Depends(get_tool_service),
):
    """List all registered tool names."""
    return sorted(tool_service.available_tools())
