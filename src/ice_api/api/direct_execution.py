"""Direct execution endpoints for quick testing and experimentation.

These endpoints provide a simpler UX for executing individual nodes (tools, agents, workflows)
while internally creating single-node blueprints to maintain consistency with the 
MCP workflow system. This ensures all executions benefit from telemetry, analysis,
and AI suggestions.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from ice_core.models.mcp import Blueprint, RunRequest, NodeSpec
from ice_core.models.llm import LLMConfig
from ice_core.models.enums import ModelProvider
from ice_api.dependencies import get_tool_service
from ice_core.unified_registry import registry, global_agent_registry
from ice_core.models import NodeType

from .mcp import start_run, get_result

router = APIRouter(tags=["direct-execution"])


class DirectExecutionRequest(BaseModel):
    """Request model for direct node execution."""
    inputs: Dict[str, Any] = {}
    options: Dict[str, Any] = {}
    wait_for_completion: bool = True
    timeout: float = 30.0


class DirectExecutionResponse(BaseModel):
    """Response model for direct execution."""
    run_id: str
    status: str  # "completed", "running", "failed"
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    telemetry_url: str
    suggestions: Optional[list[str]] = None


async def wait_for_run_completion(run_id: str, timeout: float = 30.0) -> Dict[str, Any]:
    """Poll for run completion with timeout."""
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        try:
            result = await get_result(run_id)
            return {
                "status": "completed" if result.success else "failed",
                "output": result.output,
                "error": result.error
            }
        except HTTPException as e:
            if e.status_code == 202:  # Still running
                await asyncio.sleep(0.5)
                continue
            raise
    
    return {"status": "running", "output": None, "error": "Timeout waiting for completion"}


def get_ai_suggestions(node_type: str, node_name: str, result: Dict[str, Any]) -> list[str]:
    """Get AI suggestions for next steps based on execution results."""
    # This is where Frosty's intelligence comes in
    # For now, return contextual suggestions based on node type
    
    suggestions = []
    
    if node_type == "tool":
        if node_name == "csv_reader":
            suggestions.extend([
                "Add a data validator to check data quality",
                "Use summarizer tool to get insights",
                "Apply row filtering based on conditions"
            ])
        elif node_name == "web_search":
            suggestions.extend([
                "Extract specific fields with jinja templates",
                "Summarize search results",
                "Filter results by relevance"
            ])
        else:
            suggestions.extend([
                "Chain with another tool for data transformation",
                "Add error handling with condition nodes",
                "Store results for later use"
            ])
    
    elif node_type == "agent":
        suggestions.extend([
            "Chain with another agent for complex reasoning",
            "Add human-in-the-loop validation",
            "Store results for future reference",
            "Add memory to improve context retention"
        ])
    
    elif node_type == "llm":
        suggestions.extend([
            "Add tools to create an agent for enhanced capabilities",
            "Chain with condition node for response validation",
            "Use parallel node to compare multiple model outputs",
            "Add output parsing with structured schemas"
        ])
    
    elif node_type == "condition":
        suggestions.extend([
            "Add parallel branches for complex logic trees",
            "Chain with loop node for retry logic",
            "Add workflow node to encapsulate the conditional flow",
            "Use code node for custom condition evaluation"
        ])
    
    elif node_type == "workflow":
        suggestions.extend([
            "Add monitoring and logging for workflow steps",
            "Create parallel sub-workflows for efficiency",
            "Add condition nodes for dynamic workflow paths",
            "Embed as sub-workflow in larger orchestration"
        ])
    
    elif node_type == "loop":
        suggestions.extend([
            "Add condition node to control loop termination",
            "Use parallel node for batch processing",
            "Add aggregation logic to collect loop results",
            "Implement backoff strategy for retries"
        ])
    
    elif node_type == "parallel":
        suggestions.extend([
            "Add synchronization logic for results merging",
            "Use condition nodes to handle partial failures",
            "Chain with aggregation tools for result combination",
            "Add timeout handling for long-running branches"
        ])
    
    elif node_type == "code":
        suggestions.extend([
            "Add error handling with try-catch patterns",
            "Chain with validation tools for output verification",
            "Use sandboxing for security isolation",
            "Add logging for debugging and monitoring"
        ])
    
    # Generic suggestions for all types
    if result.get("error"):
        suggestions.extend([
            "Add retry logic with exponential backoff",
            "Implement fallback strategies",
            "Add error notification mechanisms"
        ])
    
    return suggestions


@router.post("/v1/tools/{tool_name}", response_model=DirectExecutionResponse)
async def execute_tool(
    tool_name: str, 
    request: DirectExecutionRequest,
    tool_service = Depends(get_tool_service)
) -> DirectExecutionResponse:
    """Execute a single tool with the given inputs."""
    
    # Verify tool exists
    if tool_service and tool_name not in tool_service.available_tools():
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    # Create single-node blueprint
    node_id = f"{tool_name}_quick_{uuid.uuid4().hex[:8]}"
    blueprint = Blueprint(
        blueprint_id=f"quick_tool_{uuid.uuid4().hex[:8]}",
        nodes=[
            NodeSpec(
                id=node_id,
                type="tool",
                tool_name=tool_name,  # ToolNodeConfig expects tool_name
                tool_args=request.inputs,  # ToolNodeConfig expects tool_args
                # Design-time schemas for MCP validation
                # Tools typically have dict inputs and dict outputs
                input_schema={"args": "dict"},
                output_schema={"result": "dict"},
                **request.options
            )
        ]
    )
    
    # Execute through MCP
    run_request = RunRequest(blueprint=blueprint)
    run_ack = await start_run(run_request)
    
    # Wait for completion if requested
    if request.wait_for_completion:
        result = await wait_for_run_completion(run_ack.run_id, request.timeout)
    else:
        result = {"status": "running", "output": None, "error": None}
    
    return DirectExecutionResponse(
        run_id=run_ack.run_id,
        status=result["status"],
        output=result.get("output"),
        error=result.get("error"),
        telemetry_url=run_ack.events_endpoint,
        suggestions=get_ai_suggestions("tool", tool_name, result) if result["status"] == "completed" else None
    )


@router.post("/v1/agents/{agent_name}", response_model=DirectExecutionResponse)
async def execute_agent(agent_name: str, request: DirectExecutionRequest) -> DirectExecutionResponse:
    """Execute a single agent with the given inputs."""
    
    # Verify agent exists
    try:
        agent_path = global_agent_registry.get(agent_name)
        if not agent_path:
            raise KeyError()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    # Create single-node blueprint
    node_id = f"{agent_name}_quick_{uuid.uuid4().hex[:8]}"
    blueprint = Blueprint(
        blueprint_id=f"quick_agent_{uuid.uuid4().hex[:8]}",
        nodes=[
            NodeSpec(
                id=node_id,
                type="agent",
                package=agent_name,  # AgentNodeConfig expects 'package' not 'name'
                agent_config=request.inputs,  # Pass inputs as agent_config
                # Design-time schemas for MCP validation
                # Agents typically have context inputs and structured outputs
                input_schema={"context": "dict"},
                output_schema={"response": "dict"},
                **request.options
            )
        ]
    )
    
    # Execute through MCP
    run_request = RunRequest(blueprint=blueprint)
    run_ack = await start_run(run_request)
    
    # Wait for completion if requested
    if request.wait_for_completion:
        result = await wait_for_run_completion(run_ack.run_id, request.timeout)
    else:
        result = {"status": "running", "output": None, "error": None}
    
    return DirectExecutionResponse(
        run_id=run_ack.run_id,
        status=result["status"],
        output=result.get("output"),
        error=result.get("error"),
        telemetry_url=run_ack.events_endpoint,
        suggestions=get_ai_suggestions("agent", agent_name, result) if result["status"] == "completed" else None
    )


@router.post("/v1/workflows/{workflow_name}/execute", response_model=DirectExecutionResponse)
async def execute_workflow_node(workflow_name: str, request: DirectExecutionRequest) -> DirectExecutionResponse:
    """Execute a workflow as a single node with the given inputs."""
    
    # Verify workflow exists
    try:
        workflow = registry.get_instance(NodeType.WORKFLOW, workflow_name)
        if not workflow:
            raise KeyError()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")
    
    # Create single-node blueprint
    node_id = f"{workflow_name}_quick_{uuid.uuid4().hex[:8]}"
    blueprint = Blueprint(
        blueprint_id=f"quick_workflow_{uuid.uuid4().hex[:8]}",
        nodes=[
            NodeSpec(
                id=node_id,
                type="workflow",
                workflow_ref=workflow_name,
                inputs=request.inputs,
                **request.options
            )
        ]
    )
    
    # Execute through MCP
    run_request = RunRequest(blueprint=blueprint)
    run_ack = await start_run(run_request)
    
    # Wait for completion if requested
    if request.wait_for_completion:
        result = await wait_for_run_completion(run_ack.run_id, request.timeout)
    else:
        result = {"status": "running", "output": None, "error": None}
    
    return DirectExecutionResponse(
        run_id=run_ack.run_id,
        status=result["status"],
        output=result.get("output"),
        error=result.get("error"),
        telemetry_url=run_ack.events_endpoint,
        suggestions=get_ai_suggestions("workflow", workflow_name, result) if result["status"] == "completed" else None
    )


@router.post("/v1/llm/{model}", response_model=DirectExecutionResponse)
async def execute_llm(model: str, request: DirectExecutionRequest) -> DirectExecutionResponse:
    """Execute a single LLM node with the given prompt and inputs."""
    
    # Extract prompt from inputs or options
    prompt = request.inputs.get("prompt", request.options.get("prompt", ""))
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required in inputs or options")
    
    # Create single-node blueprint
    node_id = f"llm_quick_{uuid.uuid4().hex[:8]}"
    blueprint = Blueprint(
        blueprint_id=f"quick_llm_{uuid.uuid4().hex[:8]}",
        nodes=[
            NodeSpec(
                id=node_id,
                type="llm",
                model=model,
                prompt=prompt,
                llm_config=LLMConfig(
                    provider=ModelProvider(request.options.get("provider", "openai")),
                    model=model,
                    temperature=request.options.get("temperature", 0.7),
                    max_tokens=request.options.get("max_tokens", 500)
                ),
                inputs=request.inputs,
            )
        ]
    )
    
    # Execute through MCP
    run_request = RunRequest(blueprint=blueprint)
    run_ack = await start_run(run_request)
    
    # Wait for completion if requested
    if request.wait_for_completion:
        result = await wait_for_run_completion(run_ack.run_id, request.timeout)
    else:
        result = {"status": "running", "output": None, "error": None}
    
    return DirectExecutionResponse(
        run_id=run_ack.run_id,
        status=result["status"],
        output=result.get("output"),
        error=result.get("error"),
        telemetry_url=run_ack.events_endpoint,
        suggestions=get_ai_suggestions("llm", model, result) if result["status"] == "completed" else None
    )


@router.post("/v1/chains/{chain_name}", response_model=DirectExecutionResponse)
async def execute_chain(chain_name: str, request: DirectExecutionRequest) -> DirectExecutionResponse:
    """Execute a single chain with the given inputs."""
    
    # For chains, we can reference them as workflow blueprints
    # This creates a reference node that executes the chain
    node_id = f"{chain_name}_quick_{uuid.uuid4().hex[:8]}"
    blueprint = Blueprint(
        blueprint_id=f"quick_chain_{uuid.uuid4().hex[:8]}",
        nodes=[
            NodeSpec(
                id=node_id,
                type="workflow",  # Use workflow type (merged unit/nested_chain)
                workflow_ref=chain_name,  # WorkflowNodeConfig expects 'workflow_ref' field
                # Design-time schemas for MCP validation
                # Chains typically have workflow inputs and outputs
                input_schema={"inputs": "dict"},
                output_schema={"outputs": "dict"},
                **request.options
            )
        ]
    )
    
    # Execute through MCP
    run_request = RunRequest(blueprint=blueprint)
    run_ack = await start_run(run_request)
    
    # Wait for completion if requested  
    if request.wait_for_completion:
        result = await wait_for_run_completion(run_ack.run_id, request.timeout)
    else:
        result = {"status": "running", "output": None, "error": None}
    
    return DirectExecutionResponse(
        run_id=run_ack.run_id,
        status=result["status"],
        output=result.get("output"),
        error=result.get("error"),
        telemetry_url=run_ack.events_endpoint,
        suggestions=get_ai_suggestions("chain", chain_name, result) if result["status"] == "completed" else None
    ) 


@router.post("/v1/condition/{condition_name}", response_model=DirectExecutionResponse)
async def execute_condition(condition_name: str, request: DirectExecutionRequest) -> DirectExecutionResponse:
    """Execute a single condition node with the given inputs."""
    
    # Create single-node blueprint
    node_id = f"condition_quick_{uuid.uuid4().hex[:8]}"
    blueprint = Blueprint(
        blueprint_id=f"quick_condition_{uuid.uuid4().hex[:8]}",
        nodes=[
            NodeSpec(
                id=node_id,
                type="condition",
                expression=request.inputs.get("expression", "true"),
                true_branch=request.inputs.get("true_branch"),
                false_branch=request.inputs.get("false_branch"),
                inputs=request.inputs,
                **request.options
            )
        ]
    )
    
    # Execute through MCP
    run_request = RunRequest(blueprint=blueprint)
    run_ack = await start_run(run_request)
    
    # Wait for completion if requested
    if request.wait_for_completion:
        result = await wait_for_run_completion(run_ack.run_id, request.timeout)
    else:
        result = {"status": "running", "output": None, "error": None}
    
    return DirectExecutionResponse(
        run_id=run_ack.run_id,
        status=result["status"],
        output=result.get("output"),
        error=result.get("error"),
        telemetry_url=run_ack.events_endpoint,
        suggestions=get_ai_suggestions("condition", condition_name, result) if result["status"] == "completed" else None
    )


@router.post("/v1/loop/{loop_name}", response_model=DirectExecutionResponse)
async def execute_loop(loop_name: str, request: DirectExecutionRequest) -> DirectExecutionResponse:
    """Execute a single loop node with the given inputs."""
    
    # Create single-node blueprint
    node_id = f"loop_quick_{uuid.uuid4().hex[:8]}"
    blueprint = Blueprint(
        blueprint_id=f"quick_loop_{uuid.uuid4().hex[:8]}",
        nodes=[
            NodeSpec(
                id=node_id,
                type="loop",
                items_source=request.inputs.get("items_source", "items"),
                item_var=request.inputs.get("item_var", "item"),
                body_nodes=request.inputs.get("body_nodes", []),
                max_iterations=request.options.get("max_iterations", None),
                parallel=request.options.get("parallel", False),
                inputs=request.inputs,
                **request.options
            )
        ]
    )
    
    # Execute through MCP
    run_request = RunRequest(blueprint=blueprint)
    run_ack = await start_run(run_request)
    
    # Wait for completion if requested
    if request.wait_for_completion:
        result = await wait_for_run_completion(run_ack.run_id, request.timeout)
    else:
        result = {"status": "running", "output": None, "error": None}
    
    return DirectExecutionResponse(
        run_id=run_ack.run_id,
        status=result["status"],
        output=result.get("output"),
        error=result.get("error"),
        telemetry_url=run_ack.events_endpoint,
        suggestions=get_ai_suggestions("loop", loop_name, result) if result["status"] == "completed" else None
    )


@router.post("/v1/parallel/{parallel_name}", response_model=DirectExecutionResponse)
async def execute_parallel(parallel_name: str, request: DirectExecutionRequest) -> DirectExecutionResponse:
    """Execute a single parallel node with the given inputs."""
    
    # Create single-node blueprint
    node_id = f"parallel_quick_{uuid.uuid4().hex[:8]}"
    blueprint = Blueprint(
        blueprint_id=f"quick_parallel_{uuid.uuid4().hex[:8]}",
        nodes=[
            NodeSpec(
                id=node_id,
                type="parallel",
                branches=request.inputs.get("branches", []),
                max_concurrency=request.options.get("max_concurrency", None),
                merge_outputs=request.options.get("merge_outputs", True),
                inputs=request.inputs,
                **request.options
            )
        ]
    )
    
    # Execute through MCP
    run_request = RunRequest(blueprint=blueprint)
    run_ack = await start_run(run_request)
    
    # Wait for completion if requested
    if request.wait_for_completion:
        result = await wait_for_run_completion(run_ack.run_id, request.timeout)
    else:
        result = {"status": "running", "output": None, "error": None}
    
    return DirectExecutionResponse(
        run_id=run_ack.run_id,
        status=result["status"],
        output=result.get("output"),
        error=result.get("error"),
        telemetry_url=run_ack.events_endpoint,
        suggestions=get_ai_suggestions("parallel", parallel_name, result) if result["status"] == "completed" else None
    )


@router.post("/v1/code/{code_name}", response_model=DirectExecutionResponse)
async def execute_code(code_name: str, request: DirectExecutionRequest) -> DirectExecutionResponse:
    """Execute a single code node with the given inputs."""
    
    # Create single-node blueprint
    node_id = f"code_quick_{uuid.uuid4().hex[:8]}"
    blueprint = Blueprint(
        blueprint_id=f"quick_code_{uuid.uuid4().hex[:8]}",
        nodes=[
            NodeSpec(
                id=node_id,
                type="code",
                code=request.inputs.get("code", ""),
                language=request.options.get("language", "python"),
                sandbox=request.options.get("sandbox", True),
                imports=request.options.get("imports", []),
                inputs=request.inputs,
                **request.options
            )
        ]
    )
    
    # Execute through MCP
    run_request = RunRequest(blueprint=blueprint)
    run_ack = await start_run(run_request)
    
    # Wait for completion if requested
    if request.wait_for_completion:
        result = await wait_for_run_completion(run_ack.run_id, request.timeout)
    else:
        result = {"status": "running", "output": None, "error": None}
    
    return DirectExecutionResponse(
        run_id=run_ack.run_id,
        status=result["status"],
        output=result.get("output"),
        error=result.get("error"),
        telemetry_url=run_ack.events_endpoint,
        suggestions=get_ai_suggestions("code", code_name, result) if result["status"] == "completed" else None
    ) 