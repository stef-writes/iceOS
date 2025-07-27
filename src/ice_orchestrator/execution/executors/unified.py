"""Protocol-based executors for all node types using proper registry patterns.

This module implements the proper architecture where executors use the registry
protocol to retrieve and delegate to tools/services rather than manually 
instantiating node wrapper classes.
"""
from datetime import datetime
from typing import Any, Dict, TypeAlias, List
import asyncio

from ice_core.models import (
    NodeExecutionResult, NodeType,
    ToolNodeConfig, LLMOperatorConfig as LLMNodeConfig,
    AgentNodeConfig, ConditionNodeConfig, WorkflowNodeConfig
)
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike
from ice_core.unified_registry import register_node, registry
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
        from ice_orchestrator.providers.llm_service import LLMService
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

# NOTE: nested_chain executor removed - use workflow executor instead 

# NOTE: unit executor removed - merged into workflow executor


# Workflow executor - embed sub-workflows (merged unit/nested_chain)
@register_node("workflow")
async def workflow_executor(
    workflow: Workflow, cfg: Any, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute an embedded sub-workflow."""
    start_time = datetime.utcnow()
    
    try:
        from ice_core.models import WorkflowNodeConfig
        if not isinstance(cfg, WorkflowNodeConfig):
            # Legacy support for old workflow nodes
            workflow_ref = getattr(cfg, 'workflow_ref', None)
            if not workflow_ref:
                raise ValueError(f"Workflow node {cfg.id} missing workflow_ref")
        else:
            workflow_ref = cfg.workflow_ref
        
        # Get workflow from registry
        sub_workflow = registry.get_instance(NodeType.WORKFLOW, workflow_ref)
        
        # Apply config overrides if specified
        merged_ctx = {**ctx}
        if hasattr(cfg, 'config_overrides') and cfg.config_overrides:
            merged_ctx.update(cfg.config_overrides)
        
        # Execute sub-workflow
        result = await sub_workflow.execute(context=merged_ctx)
        
        # Handle exposed outputs
        output = result
        if hasattr(cfg, 'exposed_outputs') and cfg.exposed_outputs:
            # Extract only the exposed outputs
            exposed = {}
            for exposed_name, internal_path in cfg.exposed_outputs.items():
                # Navigate the result using dot notation
                value = result
                for part in internal_path.split('.'):
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
                exposed[exposed_name] = value
            output = exposed
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=True,
            output=output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="workflow",
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
                node_type="workflow",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(e).__name__,
            ),
            execution_time=duration
        )


# Loop executor - iteration over collections
@register_node("loop")
async def loop_executor(
    workflow: Workflow, cfg: Any, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a loop over a collection."""
    start_time = datetime.utcnow()
    
    try:
        from ice_core.models import LoopNodeConfig
        
        # Handle both new and legacy configurations
        if isinstance(cfg, LoopNodeConfig):
            iterator_path = cfg.items_source
            body_nodes = cfg.body_nodes
            max_iterations = cfg.max_iterations
            parallel_execution = cfg.parallel
        else:
            iterator_path = getattr(cfg, 'iterator_path', None)
            body_nodes = getattr(cfg, 'body_nodes', [])
            max_iterations = getattr(cfg, 'max_iterations', 100)
            parallel_execution = getattr(cfg, 'parallel', False)
        
        if not iterator_path:
            raise ValueError(f"Loop node {cfg.id} missing iterator_path/items")
        
        # Get the collection to iterate over from context
        # Handle both direct path and nested path resolution
        if isinstance(iterator_path, str):
            # Resolve path in context
            parts = iterator_path.split('.')
            collection = ctx
            for part in parts:
                if isinstance(collection, dict) and part in collection:
                    collection = collection[part]
                else:
                    collection = []
                    break
        else:
            # Direct collection provided
            collection = iterator_path
        
        if not isinstance(collection, (list, tuple)):
            raise ValueError(f"Loop iterator must be a list, got {type(collection)}")
        
        # Execute body for each item
        results = []
        
        if parallel_execution:
            # Execute iterations in parallel
            async def execute_iteration(item: Any, index: int) -> Dict[str, Any]:
                # Create iteration context
                loop_ctx = {**ctx, 'item': item, 'index': index}
                item_result = {}
                
                # Execute body nodes through workflow executor
                for node_id in body_nodes:
                    if hasattr(workflow, 'execute_node'):
                        node_result = await workflow.execute_node(node_id, loop_ctx)
                        item_result[node_id] = node_result.output if node_result.success else node_result.error
                    else:
                        # Fallback if workflow doesn't have execute_node
                        item_result[node_id] = {"status": "executed", "item": item}
                
                return item_result
            
            # Run all iterations concurrently
            tasks = [execute_iteration(item, i) for i, item in enumerate(collection[:max_iterations])]
            results = await asyncio.gather(*tasks)
        else:
            # Execute iterations sequentially
            for i, item in enumerate(collection[:max_iterations]):
                # Create iteration context
                loop_ctx = {**ctx, 'item': item, 'index': i}
                item_result = {}
                
                # Execute body nodes through workflow executor
                for node_id in body_nodes:
                    if hasattr(workflow, 'execute_node'):
                        node_result = await workflow.execute_node(node_id, loop_ctx)
                        item_result[node_id] = node_result.output if node_result.success else node_result.error
                    else:
                        # Fallback if workflow doesn't have execute_node
                        item_result[node_id] = {"status": "executed", "item": item}
                
                results.append(item_result)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=True,
            output={"results": results, "iterations": len(results)},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="loop",
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
                node_type="loop",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(e).__name__,
            ),
            execution_time=duration
        )


# Parallel executor - concurrent branch execution
@register_node("parallel")
async def parallel_executor(
    workflow: Workflow, cfg: Any, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute multiple branches in parallel."""
    start_time = datetime.utcnow()
    
    try:
        from ice_core.models import ParallelNodeConfig
        
        # Handle both new and legacy configurations
        if isinstance(cfg, ParallelNodeConfig):
            branches = cfg.branches
            wait_strategy = "all"  # Default strategy since it's not in the model
            merge_outputs = cfg.merge_outputs
        else:
            branches = getattr(cfg, 'branches', [])
            wait_strategy = getattr(cfg, 'wait_strategy', 'all')
            merge_outputs = getattr(cfg, 'merge_outputs', True)
        
        if not branches:
            raise ValueError(f"Parallel node {cfg.id} has no branches")
        
        # Execute all branches concurrently
        async def execute_branch(branch_nodes: List[str], branch_idx: int) -> Dict[str, Any]:
            branch_results = {}
            branch_ctx = {**ctx, 'branch_index': branch_idx}
            
            for node_id in branch_nodes:
                if hasattr(workflow, 'execute_node'):
                    node_result = await workflow.execute_node(node_id, branch_ctx)
                    branch_results[node_id] = node_result.output if node_result.success else {"error": node_result.error}
                else:
                    # Fallback if workflow doesn't have execute_node
                    branch_results[node_id] = {"status": "executed", "branch": branch_idx}
            
            return branch_results
        
        # Run branches in parallel
        tasks = [execute_branch(branch, idx) for idx, branch in enumerate(branches)]
        
        if wait_strategy == 'all':
            # Wait for all branches
            branch_results = await asyncio.gather(*tasks, return_exceptions=True)
            completed_branches = list(range(len(branches)))
        elif wait_strategy == 'any' or wait_strategy == 'race':
            # Wait for first to complete
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            branch_results = []
            completed_branches = []
            
            for idx, task in enumerate(tasks):
                if task in done:
                    try:
                        branch_results.append(await task)
                        completed_branches.append(idx)
                    except Exception as e:
                        branch_results.append({"error": str(e)})
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        else:
            raise ValueError(f"Unknown wait strategy: {wait_strategy}")
        
        # Process results and handle exceptions
        processed_results = []
        for idx, result in enumerate(branch_results):
            if isinstance(result, Exception):
                processed_results.append({"branch_error": str(result), "branch_index": idx})
            else:
                processed_results.append(result)
        
        # Merge outputs if requested
        output = {
            "branch_results": processed_results,
            "completed_branches": completed_branches,
            "strategy": wait_strategy
        }
        
        if merge_outputs and all(isinstance(r, dict) for r in processed_results):
            # Merge all branch outputs into a single dict
            merged = {}
            for branch_result in processed_results:
                if isinstance(branch_result, dict) and 'branch_error' not in branch_result:
                    # Merge node outputs from each branch
                    for node_id, node_output in branch_result.items():
                        if node_id not in merged:
                            merged[node_id] = node_output
                        else:
                            # If duplicate node IDs, create list
                            if not isinstance(merged[node_id], list):
                                merged[node_id] = [merged[node_id]]
                            merged[node_id].append(node_output)
            output["merged"] = merged
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=True,
            output=output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="parallel",
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
                node_type="parallel",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(e).__name__,
            ),
            execution_time=duration
        )


# Code executor - direct code execution
@register_node("code")
async def code_executor(
    workflow: Workflow, cfg: Any, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute arbitrary Python code in a sandboxed environment."""
    from datetime import datetime
    start_time = datetime.utcnow()
    
    try:
        from ice_core.models import CodeNodeConfig
        import ast
        
        # Handle both new and legacy configurations
        if isinstance(cfg, CodeNodeConfig):
            code = cfg.code
            language = cfg.language
            timeout = 30  # Default timeout since it's not in the model
            imports = cfg.imports
        else:
            code = getattr(cfg, 'code', '')
            language = getattr(cfg, 'runtime', 'python')
            timeout = getattr(cfg, 'timeout', 30)
            imports = getattr(cfg, 'imports', [])
        
        if not code:
            raise ValueError(f"Code node {cfg.id} has no code")
        
        if language != 'python':
            raise ValueError(f"Only Python runtime supported, got {language}")
        
        # Validate code syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")
        
        # Create sandboxed namespace with limited builtins
        safe_builtins = {
            # Math functions
            'abs': abs, 'round': round, 'min': min, 'max': max, 'sum': sum,
            # Type conversions
            'int': int, 'float': float, 'str': str, 'bool': bool,
            # Data structures
            'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
            # Utilities
            'len': len, 'range': range, 'enumerate': enumerate, 'zip': zip,
            'map': map, 'filter': filter, 'sorted': sorted, 'reversed': reversed,
            # Safe I/O
            'print': print,  # Could be redirected to capture output
        }
        
        # Add allowed imports
        import_namespace = {}
        for imp in imports:
            if imp == 'json':
                import json
                import_namespace['json'] = json
            elif imp == 'datetime':
                import datetime
                import_namespace['datetime'] = datetime
            elif imp == 'math':
                import math
                import_namespace['math'] = math
            elif imp == 're':
                import re
                import_namespace['re'] = re
            # Add more safe imports as needed
        
        # Create execution namespace
        namespace = {
            '__builtins__': safe_builtins,
            'ctx': ctx.copy(),  # Provide copy of context
            'inputs': ctx.copy(),  # Alias for backwards compatibility
            'output': {},  # Expected output dict
            **import_namespace
        }
        
        # Execute code with timeout
        # In production, this should use proper process isolation
        import asyncio
        
        async def execute_with_timeout():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, exec, code, namespace)
        
        try:
            await asyncio.wait_for(execute_with_timeout(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Code execution exceeded timeout of {timeout}s")
        
        # Get output from namespace
        output = namespace.get('output', {})
        
        # If output is empty, try to capture last expression value
        if not output and 'result' in namespace:
            output = {'result': namespace['result']}
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=True,
            output=output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="code",
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
                node_type="code",
                name=cfg.name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(e).__name__,
            ),
            execution_time=duration
        ) 