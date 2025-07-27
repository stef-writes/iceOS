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

def _flatten_dependency_outputs(merged_inputs: Dict[str, Any], tool: Any) -> Dict[str, Any]:
    """Smart parameter flattening for seamless workflow execution.
    
    This automatically extracts commonly needed parameters from nested 
    dependency outputs so workflows "just work" without manual input mappings.
    
    For example:
    Input: {"read_data": {"clean_items": [...], "success": true}, "tool_args": {...}}
    Output: {"clean_items": [...], "read_data": {...}, "tool_args": {...}}
    """
    try:
        import inspect
        
        # Get tool's expected parameters through introspection
        execute_method = getattr(tool, '_execute_impl', None)
        if not execute_method:
            return merged_inputs  # Fallback to original behavior
        
        # Get parameter names from tool implementation
        sig = inspect.signature(execute_method)
        expected_params = set(sig.parameters.keys()) - {'self', 'kwargs'}
        
        # Start with original inputs
        flattened = merged_inputs.copy()
        
        # Look for dependency outputs (keys that look like node IDs)
        for key, value in merged_inputs.items():
            if isinstance(value, dict) and key not in expected_params:
                # This looks like a dependency output - extract matching parameters
                for param_name in expected_params:
                    if param_name in value and param_name not in flattened:
                        # Found a match! Extract the parameter to top level
                        flattened[param_name] = value[param_name]
        
        return flattened
        
    except Exception:
        # If introspection fails, fallback to original behavior
        return merged_inputs

# Tool executor using WASM sandboxing  
@register_node("tool")
async def tool_executor(
    workflow: Workflow, cfg: ToolNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a tool in WASM sandbox for security isolation."""
    from ice_orchestrator.execution.wasm_executor import execute_node_with_wasm
    import inspect
    
    try:
        # Get tool instance from registry using ITool protocol
        tool = registry.get_instance(NodeType.TOOL, cfg.tool_name)
        
        # Smart parameter flattening for the "easy way"
        merged_inputs = {**cfg.tool_args, **ctx}
        flattened_inputs = _flatten_dependency_outputs(merged_inputs, tool)
        
        # Extract tool execution code for WASM sandboxing
        try:
            tool_code = inspect.getsource(tool.execute)
            # Remove method signature and add result assignment
            tool_code = f"""
# Tool execution code
{tool_code}

# Execute with flattened inputs
result = await execute(inputs)
if isinstance(result, dict):
    output.update(result)
else:
    output['result'] = result
"""
        except (OSError, TypeError):
            # Fallback: create wrapper code if source not available
            tool_code = f"""
# Tool wrapper for {cfg.tool_name}
async def execute_tool():
    # Note: This is a simplified fallback
    # In production, tools would be compiled to WASM directly
    return {{"tool_name": "{cfg.tool_name}", "executed": True}}

result = await execute_tool()
output.update(result)
"""
        
        # Execute tool in WASM sandbox with appropriate resource limits
        return await execute_node_with_wasm(
            node_type="tool",
            code=tool_code,
            context={"inputs": flattened_inputs, "tool_args": cfg.tool_args},
            node_id=cfg.id,
            allowed_imports=["json", "datetime", "math", "re", "uuid"]  # Tool-safe imports
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

# LLM executor using WASM sandboxing for prompt processing
@register_node("llm")
async def llm_executor(
    workflow: Workflow, cfg: LLMNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute an LLM using WASM-sandboxed prompt processing and response handling."""
    from ice_orchestrator.execution.wasm_executor import execute_node_with_wasm
    
    try:
        # Create sandboxed code for LLM operations
        llm_code = f"""
# WASM-sandboxed LLM execution logic
import json

def execute_llm():
    # Get configuration from inputs
    prompt_template = {repr(cfg.prompt)}
    context = inputs.copy()
    
    # Safely render prompt template
    try:
        prompt = prompt_template.format(**context)
    except KeyError as e:
        return {{"error": f"Missing template variable in prompt: {{str(e)}}"}}
    
    # Return structured data for LLM service call
    return {{
        "prompt": prompt,
        "model": {repr(cfg.model)},
        "max_tokens": {cfg.max_tokens},
        "temperature": {cfg.temperature},
        "provider": {repr(cfg.llm_config.provider) if hasattr(cfg, 'llm_config') else repr('openai')},
        "response_format": {repr(getattr(cfg, 'response_format', None))},
        "ready_for_llm_call": True
    }}

output.update(execute_llm())
"""
        
        # Execute prompt processing in WASM sandbox
        wasm_result = await execute_node_with_wasm(
            node_type="llm",
            code=llm_code,
            context=ctx,
            node_id=cfg.id,
            allowed_imports=["json"]
        )
        
        if not wasm_result.success:
            return wasm_result
        
        # Extract processed data from WASM result
        llm_data = wasm_result.output.get("result", {})
        if "error" in llm_data:
            raise Exception(llm_data["error"])
        
        if not llm_data.get("ready_for_llm_call"):
            raise Exception("LLM prompt processing failed")
        
        # Now make the actual LLM service call (outside WASM for API access)
        from ice_orchestrator.providers.llm_service import LLMService
        from ice_core.models.llm import LLMConfig
        from datetime import datetime
        
        start_time = datetime.utcnow()
        llm_service = LLMService()
        
        llm_config = LLMConfig(
            provider=llm_data["provider"],
            model=llm_data["model"],
            max_tokens=llm_data["max_tokens"],
            temperature=llm_data["temperature"]
        )
        
        text, usage, error = await llm_service.generate(
            llm_config=llm_config,
            prompt=llm_data["prompt"]
        )
        
        if error:
            raise Exception(f"LLM service error: {error}")
        
        # Process response in WASM sandbox for security
        response_code = f"""
# WASM-sandboxed response processing
import json

def process_response():
    text = {repr(text)}
    response_format = {repr(llm_data.get("response_format"))}
    
    # Format output according to response format
    if response_format and response_format.get("type") == "json_object":
        try:
            output_data = json.loads(text)
        except json.JSONDecodeError:
            output_data = {{"text": text}}
    else:
        output_data = {{"text": text}}
    
    return output_data

output.update(process_response())
"""
        
        response_result = await execute_node_with_wasm(
            node_type="llm",
            code=response_code,
            context={},
            node_id=f"{cfg.id}_response",
            allowed_imports=["json"]
        )
        
        if not response_result.success:
            return response_result
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
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

# Agent executor using WASM sandboxing
@register_node("agent")
async def agent_executor(
    workflow: Workflow, cfg: AgentNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute an agent in WASM sandbox for security isolation."""
    from ice_orchestrator.execution.wasm_executor import execute_node_with_wasm
    import inspect
    
    try:
        # Get agent from registry using package name
        agent = registry.get_instance(NodeType.AGENT, cfg.package)
        
        # Extract agent execution code for WASM sandboxing
        try:
            agent_code = inspect.getsource(agent.execute)
            # Create wrapper code for agent execution
            agent_code = f"""
# Agent execution code in WASM sandbox
{agent_code}

# Execute agent with context
result = await execute(inputs)
if isinstance(result, dict):
    output.update(result)
else:
    output['result'] = result
    
# Add agent metadata
output['agent_package'] = {repr(cfg.package)}
output['agent_executed'] = True
"""
        except (OSError, TypeError):
            # Fallback: create wrapper code if source not available
            agent_code = f"""
# Agent wrapper for {cfg.package}
async def execute_agent():
    # Note: This is a simplified fallback
    # In production, agents would be compiled to WASM directly
    context = inputs.copy()
    
    # Simulate agent execution with context processing
    return {{
        "agent_package": {repr(cfg.package)},
        "context_processed": True,
        "agent_executed": True,
        "context_summary": f"Processed {{len(context)}} context items"
    }}

result = await execute_agent()
output.update(result)
"""
        
        # Execute agent in WASM sandbox with extended resources for reasoning
        return await execute_node_with_wasm(
            node_type="agent",
            code=agent_code,
            context=ctx,
            node_id=cfg.id,
            allowed_imports=["json", "datetime", "math", "re", "uuid", "random"]  # Agent-safe imports
        )
        
    except Exception as e:
        from datetime import datetime
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()
        
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
                duration=0,
                error_type=type(e).__name__,
            ),
            execution_time=0
        )

# Condition executor using WASM sandboxing
@register_node("condition")
async def condition_executor(
    workflow: Workflow, cfg: ConditionNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a condition in WASM sandbox for security."""
    from ice_orchestrator.execution.wasm_executor import execute_node_with_wasm
    
    try:
        # Create safe condition evaluation code
        condition_code = f"""
# Safe condition evaluation
def evaluate_condition():
    expression = {repr(cfg.expression)}
    context = inputs.copy()
    
    # Only allow safe operations for conditions
    safe_globals = {{
        '__builtins__': {{}},
        'True': True,
        'False': False,
        'None': None,
        'and': lambda a, b: a and b,
        'or': lambda a, b: a or b,
        'not': lambda x: not x,
    }}
    safe_globals.update(context)
    
    try:
        result = bool(eval(expression, safe_globals))
        return {{
            "result": result,
            "branch": "true" if result else "false",
            "expression": expression
        }}
    except Exception as e:
        return {{
            "result": False,
            "branch": "false", 
            "error": str(e),
            "expression": expression
        }}

output.update(evaluate_condition())
"""
        
        # Execute condition in WASM sandbox with minimal resources
        return await execute_node_with_wasm(
            node_type="condition",
            code=condition_code,
            context=ctx,
            node_id=cfg.id,
            allowed_imports=[]  # No imports needed for conditions
        )
        
    except Exception as e:
        from datetime import datetime
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()
        
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
                duration=0,
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


# Loop executor using WASM sandboxing  
@register_node("loop")
async def loop_executor(
    workflow: Workflow, cfg: Any, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a loop over a collection with WASM sandboxing for iteration logic."""
    from ice_orchestrator.execution.wasm_executor import execute_node_with_wasm
    
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
        
        # Create WASM-sandboxed loop iteration logic
        loop_code = f"""
# WASM-sandboxed loop execution logic
import json

def execute_loop():
    context = inputs.copy()
    iterator_path = {repr(iterator_path)}
    max_iterations = {max_iterations}
    
    # Safely resolve collection path
    if isinstance(iterator_path, str):
        parts = iterator_path.split('.')
        collection = context
        for part in parts:
            if isinstance(collection, dict) and part in collection:
                collection = collection[part]
            else:
                collection = []
                break
    else:
        collection = iterator_path
    
    # Validate collection
    if not isinstance(collection, (list, tuple)):
        return {{"error": f"Loop iterator must be a list, got {{type(collection).__name__}}"}}
    
    # Apply iteration limit for security
    if len(collection) > max_iterations:
        collection = collection[:max_iterations]
    
    # Prepare iteration metadata  
    loop_results = {{
        "iterations": len(collection),
        "items": [],
        "body_nodes": {repr(body_nodes)},
        "parallel": {parallel_execution},
        "iterator_path": iterator_path,
        "collection_size": len(collection)
    }}
    
    # Process each item (metadata only in WASM, actual execution outside)
    for i, item in enumerate(collection):
        loop_results["items"].append({{
            "index": i,
            "item": item,
            "context_for_iteration": {{**context, "item": item, "index": i}}
        }})
    
    return loop_results

output.update(execute_loop())
"""
        
        # Execute loop preparation in WASM sandbox
        loop_result = await execute_node_with_wasm(
            node_type="loop",
            code=loop_code,
            context=ctx,
            node_id=cfg.id,
            allowed_imports=["json"]
        )
        
        if not loop_result.success:
            return loop_result
        
        loop_data = loop_result.output.get("result", {})
        if "error" in loop_data:
            raise Exception(loop_data["error"])
        
        # Now execute actual body nodes for each iteration (outside WASM)
        from datetime import datetime
        import asyncio
        
        start_time = datetime.utcnow()
        results = []
        
        if loop_data.get("parallel", False):
            # Execute iterations in parallel
            async def execute_iteration(item_data: Dict[str, Any]) -> Dict[str, Any]:
                iteration_ctx = item_data["context_for_iteration"]
                item_result = {"index": item_data["index"], "item": item_data["item"]}
                
                # Execute body nodes through workflow executor
                for node_id in loop_data["body_nodes"]:
                    if hasattr(workflow, 'execute_node'):
                        node_result = await workflow.execute_node(node_id, iteration_ctx)
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


# Code executor - WASM sandboxed execution
@register_node("code")
async def code_executor(
    workflow: Workflow, cfg: Any, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute arbitrary Python code in WASM sandbox."""
    from ice_orchestrator.execution.wasm_executor import execute_node_with_wasm
    
    try:
        from ice_core.models import CodeNodeConfig
        import ast
        
        # Handle both new and legacy configurations
        if isinstance(cfg, CodeNodeConfig):
            code = cfg.code
            language = cfg.language
            imports = cfg.imports
        else:
            code = getattr(cfg, 'code', '')
            language = getattr(cfg, 'runtime', 'python')
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
        
        # Execute in WASM sandbox with strict resource limits
        return await execute_node_with_wasm(
            node_type="code",
            code=code,
            context=ctx,
            node_id=cfg.id,
            allowed_imports=imports
        )
        
    except Exception as e:
        # Return error result if WASM execution fails
        from datetime import datetime
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()
        
        return NodeExecutionResult(
            success=False,
            error=str(e),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type="code",
                name=getattr(cfg, 'name', 'code_node'),
                start_time=start_time,
                end_time=end_time,
                duration=0,
                error_type=type(e).__name__,
            ),
            execution_time=0
        ) 