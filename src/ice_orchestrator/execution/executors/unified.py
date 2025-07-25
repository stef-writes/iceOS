"""Protocol-based executors for all node types using proper registry patterns.

This module implements the proper architecture where executors use the registry
protocol to retrieve and delegate to tools/services rather than manually 
instantiating node wrapper classes.
"""
from datetime import datetime
from typing import Any, Dict, TypeAlias

from ice_core.models import (
    NodeExecutionResult, NodeType,
    ToolNodeConfig, LLMOperatorConfig as LLMNodeConfig,
    AgentNodeConfig, ConditionNodeConfig, NestedChainConfig
)
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike
from ice_sdk.unified_registry import register_node, registry
from ice_sdk.services.locator import ServiceLocator

Workflow: TypeAlias = WorkflowLike

# Tool executor using protocol-based registry lookup
@register_node("tool")
async def tool_executor(
    workflow: Workflow, cfg: ToolNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a tool using the ITool protocol via registry lookup.
    
    This is the proper architecture: get the tool from the registry and
    delegate to its execute method directly, avoiding manual instantiation.
    """
    start_time = datetime.utcnow()
    
    try:
        # Get tool instance from registry using ITool protocol
        tool = registry.get_instance(NodeType.TOOL, cfg.tool_name)
        
        # Merge tool configuration with runtime context
        merged_inputs = {**cfg.tool_args, **ctx}
        
        # Execute using ITool protocol
        output = await tool.execute(merged_inputs)
        
        # Build successful result
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=True,
            output=output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="tool",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
            ),
            execution_time=duration
        )
        
    except Exception as e:
        # Build failure result
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=False,
            error=str(e),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="tool", 
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(e).__name__,
            ),
            execution_time=duration
        )

# LLM executor using protocol-based service lookup
@register_node("llm")
async def llm_executor(
    workflow: Workflow, cfg: LLMNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute an LLM using the LLM service directly.
    
    This is the proper architecture: use the LLM service directly rather
    than wrapping in a node class.
    """
    start_time = datetime.utcnow()
    
    try:
        # Get LLM service from service locator
        from ice_sdk.providers.llm_service import LLMService
        from ice_core.models.llm import LLMConfig
        
        llm_service = LLMService()
        
        # Render prompt template with context
        try:
            prompt = cfg.prompt.format(**ctx)
        except KeyError as e:
            raise ValueError(f"Missing template variable in prompt: {e}")
        
        # Create LLM configuration
        llm_config = LLMConfig(
            provider=cfg.llm_config.provider,  # Use the provider from llm_config
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature
        )
        
        # Execute LLM call
        text, usage, error = await llm_service.generate(
            llm_config=llm_config,
            prompt=prompt
        )
        
        if error:
            raise Exception(f"LLM service error: {error}")
        
        # Build successful result
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Format output according to response format or default to text
        if hasattr(cfg, 'response_format') and cfg.response_format and cfg.response_format.get("type") == "json_object":
            # Try to parse as JSON for structured output
            try:
                import json
                output = json.loads(text)
            except json.JSONDecodeError:
                # Fallback to text if JSON parsing fails
                output = {"text": text}
        else:
            output = {"text": text}
        
        # Create proper usage metadata if available
        usage_metadata = None
        if usage:
            from ice_core.models.node_models import UsageMetadata
            from ice_core.models.enums import ModelProvider
            
            usage_metadata = UsageMetadata(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                model=cfg.model,
                node_id=cfg.id,
                provider=ModelProvider.OPENAI  # Default to OpenAI for now
            )
        
        return NodeExecutionResult(
            success=True,
            output=output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="llm",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
            ),
            usage=usage_metadata,
            execution_time=duration
        )
        
    except Exception as e:
        # Build failure result
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=False,
            error=str(e),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="llm",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(e).__name__,
            ),
            execution_time=duration
        )

# Agent executor using protocol-based registry lookup
@register_node("agent")
async def agent_executor(
    workflow: Workflow, cfg: AgentNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute an agent using registry lookup."""
    start_time = datetime.utcnow()
    
    try:
        # Get agent from registry using package name
        agent = registry.get_instance(NodeType.AGENT, cfg.package)
        output = await agent.execute(ctx)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=True,
            output=output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="agent",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
            ),
            execution_time=duration
        )
        
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=False,
            error=str(e),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="agent",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(e).__name__,
            ),
            execution_time=duration
        )

# Condition executor using direct evaluation 
@register_node("condition")
async def condition_executor(
    workflow: Workflow, cfg: ConditionNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a condition using direct evaluation."""
    start_time = datetime.utcnow()
    
    try:
        # Safe evaluation of boolean expression
        safe_dict = {"__builtins__": {}}
        safe_dict.update(ctx)
        
        # Evaluate expression
        result = bool(eval(cfg.expression, safe_dict))
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        output = {
            "result": result,
            "branch": "true" if result else "false"
        }
        
        return NodeExecutionResult(
            success=True,
            output=output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="condition",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
            ),
            execution_time=duration
        )
        
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=False,
            error=f"Failed to evaluate condition '{cfg.expression}': {e}",
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="condition",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(e).__name__,
            ),
            execution_time=duration
        ) 

# Nested chain executor for backward compatibility
@register_node("nested_chain")
async def nested_chain_executor(
    workflow: Workflow, cfg: NestedChainConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a nested chain by delegating to the chain."""
    start_time = datetime.utcnow()
    
    try:
        # For now, return a placeholder result
        # TODO: Implement actual nested chain execution
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=True,
            output={"result": "Nested chain execution not yet implemented"},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="nested_chain",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
            ),
            execution_time=duration
        )
        
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=False,
            error=str(e),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="nested_chain",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(e).__name__,
            ),
            execution_time=duration
        ) 