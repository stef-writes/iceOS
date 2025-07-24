"""Unified executors for all node types using the new node system."""
from datetime import datetime
from typing import Any, Dict, TypeAlias

from ice_core.models import (
    NodeExecutionResult, NodeMetadata,
    ToolNodeConfig, LLMNodeConfig, UnitNodeConfig,
    AgentNodeConfig, WorkflowNodeConfig, ConditionNodeConfig,
    LoopNodeConfig, ParallelNodeConfig, CodeNodeConfig
)
from ice_core.protocols.workflow import ScriptChainLike
from ice_sdk.unified_registry import register_node
from ice_orchestrator.nodes import (
    ToolNode, LLMNode, UnitNode, AgentNode,
    WorkflowNode, ConditionNode, LoopNode,
    ParallelNode, CodeNode
)

ScriptChain: TypeAlias = ScriptChainLike

# Tool executor using new ToolNode
@register_node("tool")
async def tool_executor(
    chain: ScriptChain, cfg: ToolNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a tool node using the new unified system."""
    node = ToolNode(tool_ref=cfg.tool_ref, tool_args=cfg.tool_args)
    return await node.execute(ctx)

# LLM executor using new LLMNode
@register_node("llm")
async def llm_executor(
    chain: ScriptChain, cfg: LLMNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute an LLM node using the new unified system."""
    node = LLMNode(
        model=cfg.model,
        prompt_template=cfg.prompt_template,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        response_format=cfg.response_format,
        provider=getattr(cfg, 'provider', 'openai')
    )
    return await node.execute(ctx)

# Unit executor
@register_node("unit")
async def unit_executor(
    chain: ScriptChain, cfg: UnitNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a unit node."""
    node = UnitNode(
        unit_ref=cfg.unit_ref,
        nodes=getattr(cfg, 'nodes', [])
    )
    return await node.execute(ctx)

# Agent executor (keep existing one if it works better)
# @register_node("agent")  # Commented out - already registered elsewhere
async def agent_executor(
    chain: ScriptChain, cfg: AgentNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute an agent node."""
    node = AgentNode(
        agent_ref=cfg.agent_ref,
        tools=cfg.tools,
        max_iterations=cfg.max_iterations,
        memory_config=cfg.memory_config
    )
    return await node.execute(ctx)

# Workflow executor
@register_node("workflow")
async def workflow_executor(
    chain: ScriptChain, cfg: WorkflowNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a workflow node."""
    node = WorkflowNode(workflow_ref=cfg.workflow_ref)
    return await node.execute(ctx)

# Condition executor (updated to use new ConditionNode)
@register_node("condition")
async def condition_executor(
    chain: ScriptChain, cfg: ConditionNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a condition node."""
    node = ConditionNode(
        expression=cfg.expression,
        true_nodes=cfg.true_nodes,
        false_nodes=cfg.false_nodes
    )
    return await node.execute(ctx)

# Loop executor
@register_node("loop")
async def loop_executor(
    chain: ScriptChain, cfg: LoopNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a loop node."""
    node = LoopNode(
        iterator_path=cfg.iterator_path,
        body_nodes=cfg.body_nodes,
        max_iterations=cfg.max_iterations
    )
    return await node.execute(ctx)

# Parallel executor
@register_node("parallel")
async def parallel_executor(
    chain: ScriptChain, cfg: ParallelNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a parallel node."""
    node = ParallelNode(
        branches=cfg.branches,
        wait_strategy=cfg.wait_strategy
    )
    return await node.execute(ctx)

# Code executor
@register_node("code")
async def code_executor(
    chain: ScriptChain, cfg: CodeNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a code node."""
    node = CodeNode(
        code=cfg.code,
        runtime=cfg.runtime
    )
    return await node.execute(ctx) 