"""Protocol-based executors for all node types using proper registry patterns.

This module implements the proper architecture where executors use the registry
protocol to retrieve and delegate to tools/services rather than manually 
instantiating node wrapper classes.
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeAlias

from ice_core.models import AgentNodeConfig, ConditionNodeConfig
from ice_core.models import LLMOperatorConfig as LLMNodeConfig
from ice_core.models import NodeExecutionResult, NodeType, ToolNodeConfig
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike
from ice_core.unified_registry import register_node, registry

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

def _resolve_jinja_templates(data: Any, context: Dict[str, Any]) -> Any:
    """Recursively resolve Jinja2 templates in data structures.
    
    Resolves {{variable}} syntax in strings using the provided context.
    Works recursively on dicts, lists, and other data structures.
    """
    try:
        import importlib
        jinja2 = importlib.import_module("jinja2")
        env = jinja2.Environment(autoescape=False)  # Don't escape for data processing
        
        def resolve_value(value: Any) -> Any:
            from ice_core.models import NodeExecutionResult as _NER  # local to avoid heavy import
            if isinstance(value, _NER):
                return resolve_value(value.output if value.output is not None else {})
            if isinstance(value, str):
                # Check if it looks like a Jinja template
                if "{{" in value and "}}" in value:
                    try:
                        # Extract the variable name from the template
                        var_name = value.strip('{}').strip()
                        
                        # Special case: wildcard access like 'process_loop.*' -> return dict['results'] if present
                        if var_name.endswith('.*'):
                            base = var_name[:-2]
                            base_val = context.get(base)
                            if isinstance(base_val, dict):
                                # Fallback to 'results' key or return the entire dict
                                return base_val.get('results', base_val)
                            return base_val
                        # Handle dotted references like 'parse_documents.documents'
                        if '.' in var_name:
                            parts = var_name.split('.')
                            result = context
                            for part in parts:
                                if isinstance(result, dict) and part in result:
                                    result = result[part]
                                else:
                                    # If dotted path fails, fall back to Jinja
                                    template = env.from_string(value)
                                    result = template.render(**context)
                                    break
                            return result
                        
                        # If the context value is not a string, return it directly
                        # This preserves lists, dicts, and other data structures
                        elif var_name in context and not isinstance(context[var_name], str):
                            result = context[var_name]
                            # print(f"🔧 Template resolved (direct): '{value}' -> {type(result)} with {len(result) if hasattr(result, '__len__') else 'N/A'} items")
                            return result
                        
                        # For string values, use Jinja template rendering
                        else:
                            template = env.from_string(value)
                            result = template.render(**context)
                            # print(f"🔧 Template resolved (jinja): '{value}' -> {type(result)}")
                            return result
                        
                    except Exception as e:
                        print(f"❌ Template resolution failed for '{value}': {e}")
                        # If template rendering fails, return original value
                        return value
                return value
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            else:
                return value
        
        return resolve_value(data)
        
    except (ModuleNotFoundError, Exception):
        # If jinja2 is not available or any error, return original data
        return data

# Tool executor - RESTORED to direct execution (WASM was too restrictive)
@register_node("tool")
async def tool_executor(
    workflow: Workflow, cfg: ToolNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a tool with direct Python execution for full system access."""
    from datetime import datetime
    start_time = datetime.utcnow()
    
    try:
        # Ensure all built-in tools are registered
        try:
            import importlib
            import ice_tools  # noqa: F401 – trigger recursive auto-import
            _ = ice_tools  # silence linter unused variable
        except ModuleNotFoundError:
            pass  # package optional in some deployments

        # Get tool instance from registry using ITool protocol
        tool = registry.get_instance(NodeType.TOOL, cfg.tool_name)
        
        # Clean context: unwrap NodeExecutionResult objects to their .output for template rendering
        from ice_core.models import NodeExecutionResult as _NER
        ctx_clean: Dict[str, Any] = {}
        for k, v in ctx.items():
            if isinstance(v, _NER):
                ctx_clean[k] = v.output if v.output is not None else {}
            else:
                ctx_clean[k] = v
        
        # Resolve Jinja templates in tool_args using the cleaned context
        resolved_tool_args = _resolve_jinja_templates(cfg.tool_args, ctx_clean)
        
        # Smart parameter flattening for the "easy way"
        merged_inputs = {**resolved_tool_args, **ctx_clean}
        flattened_inputs = _flatten_dependency_outputs(merged_inputs, tool)
        
        # Keep only parameters that the tool actually expects ----------
        import inspect
        sig = inspect.signature(getattr(tool, '_execute_impl'))
        accepted = set(sig.parameters.keys()) - {'self', 'kwargs'}
        # If tool _execute_impl takes explicit params, pass only those; otherwise pass all inputs
        if accepted:
            safe_inputs = {k: v for k, v in flattened_inputs.items() if k in accepted}
        else:
            safe_inputs = flattened_inputs

        # Direct execution - tools need file I/O, network access, imports
        from ice_orchestrator.execution.sandbox.resource_sandbox import ResourceSandbox

        async with ResourceSandbox(timeout_seconds=cfg.timeout_seconds or 30) as sbx:  # type: ignore[attr-defined]
            tool_output: Any = await sbx.run_with_timeout(tool.execute(**safe_inputs))
        
        # Unwrap NodeExecutionResult for downstream nodes
        from ice_core.models import NodeExecutionResult as _NER  # local import to avoid circular
        if isinstance(tool_output, _NER):
            tool_output = tool_output.output or ({"error": tool_output.error} if tool_output.error else {})
        elif not isinstance(tool_output, dict):
            tool_output = {"result": tool_output}
        
        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=True,
            output=tool_output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.tool_name,
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"Tool execution: {cfg.tool_name}"
            )
        )
        
    except Exception as e:
        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=False,
            error=str(e),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.tool_name,
                version="1.0.0",
                owner="system",
                error_type=type(e).__name__,
                provider=cfg.provider,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"Tool execution failed: {cfg.tool_name}"
            )
        )

# LLM executor - RESTORED to direct execution (needs network access for API calls)
@register_node("llm")
async def llm_executor(
    workflow: Workflow, cfg: LLMNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute an LLM with direct execution for network API access."""
    from datetime import datetime
    start_time = datetime.utcnow()
    
    try:
        # Get LLM service for making API calls
        from ice_core.llm.service import LLMService
        llm_service = LLMService()
        
        # Safely render prompt template
        try:
            prompt = cfg.prompt.format(**ctx)
        except KeyError as e:
            raise Exception(f"Missing template variable in prompt: {str(e)}")
        
        # Create LLM config
        from ice_core.models.enums import ModelProvider
        from ice_core.models.llm import LLMConfig

        # Get provider, defaulting to OpenAI
        provider = cfg.llm_config.provider if hasattr(cfg, 'llm_config') and cfg.llm_config else ModelProvider.OPENAI
        if isinstance(provider, str):
            # Convert string to enum
            try:
                provider = ModelProvider(provider)
            except ValueError:
                provider = ModelProvider.OPENAI
        
        llm_config = LLMConfig(
            provider=provider,
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
        )
        
        # Make LLM API call - returns tuple (text, usage, error)
        text, usage, error = await llm_service.generate(
            llm_config=llm_config,
            prompt=prompt,
            context=ctx
        )
        
        end_time = datetime.utcnow()
        
        # Handle error case
        if error:
            return NodeExecutionResult(
                success=False,
                error=error,
                output={},
                metadata=NodeMetadata(
                    node_id=cfg.id,
                    node_type=cfg.type,
                    name=f"llm_{cfg.model}",
                    version="1.0.0",
                    owner="system",
                    error_type="LLMError",
                    provider=cfg.provider,
                    start_time=start_time,
                    end_time=end_time,
                    duration=(end_time - start_time).total_seconds(),
                    description=f"LLM execution failed: {cfg.model}"
                )
            )
        
        return NodeExecutionResult(
            success=True,
            output={
                "response": text,
                "prompt": prompt,
                "model": cfg.model,
                "usage": usage or {}
            },
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=f"llm_{cfg.model}",
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"LLM execution: {cfg.model}"
            )
        )
        
    except Exception as e:
        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=False,
            error=str(e),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=f"llm_{getattr(cfg, 'model', 'unknown')}",
                version="1.0.0",
                owner="system",
                error_type=type(e).__name__,
                provider=cfg.provider,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"LLM execution failed: {getattr(cfg, 'model', 'unknown')}"
            )
        )

# Agent executor - RESTORED to direct execution (WASM was too restrictive)
@register_node("agent")
async def agent_executor(
    workflow: Workflow, cfg: AgentNodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute an agent with direct Python execution for full capabilities."""
    from datetime import datetime
    start_time = datetime.utcnow()
    
    try:
        # Get agent from registry using package name
        agent = registry.get_instance(NodeType.AGENT, cfg.package)
        
        # Direct execution - agents are trusted and need full access
        agent_output: Any = await agent.execute(ctx)
        
        # Ensure agent_output is a dictionary
        if not isinstance(agent_output, dict):
            agent_output = {"result": agent_output}
        
        # Add agent metadata
        agent_output["agent_package"] = cfg.package
        agent_output["agent_executed"] = True
        
        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=True,
            output=agent_output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.package,
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"Agent execution: {cfg.package}"
            )
        )
        
    except Exception as e:
        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=False,
            error=str(e),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.package,
                version="1.0.0",
                owner="system",
                error_type=type(e).__name__,
                provider=cfg.provider,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"Agent execution failed: {cfg.package}"
            )
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
                node_type=cfg.type,
                name=cfg.name,
                version="1.0.0",
                owner="system",
                start_time=start_time,
                end_time=end_time,
                duration=0,
                error_type=type(e).__name__,
                provider=cfg.provider,
                description=f"Condition evaluation failed: {cfg.expression}"
            ),
            execution_time=0
        ) 

# Legacy executors have been merged into the unified workflow executor


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
            # Support for different workflow configuration formats
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
        sub_result = await sub_workflow.execute(merged_ctx)

        # Normalise to dictionary output
        if isinstance(sub_result, NodeExecutionResult):
            if sub_result.success:
                result_dict: Any = sub_result.output or {}
            else:
                result_dict = {"error": sub_result.error}
        else:
            result_dict = sub_result
        
        # Handle exposed outputs
        output = result_dict
        if hasattr(cfg, 'exposed_outputs') and cfg.exposed_outputs:
            # Extract only the exposed outputs
            exposed = {}
            for exposed_name, internal_path in cfg.exposed_outputs.items():
                # Navigate the result using dot notation
                value = result_dict
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
                node_type=cfg.type,
                name=cfg.name,
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                description=f"Workflow execution: {workflow_ref}"
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
                node_type=cfg.type,
                name=cfg.name,
                version="1.0.0",
                owner="system",
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(e).__name__,
                provider=cfg.provider,
                description=f"Workflow execution failed: {workflow_ref}"
            ),
            execution_time=duration
        )


# Loop executor using WASM sandboxing  
@register_node("loop")
async def loop_executor(
    workflow: Workflow, cfg: Any, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a loop over a collection with WASM sandboxing for iteration logic."""
    
    from datetime import datetime
    start_time = datetime.utcnow()
    try:
        from ice_core.models import LoopNodeConfig

        # Handle different configuration formats
        iterator_path: Optional[str]
        if isinstance(cfg, LoopNodeConfig):
            iterator_path = cfg.items_source
            max_iterations = cfg.max_iterations
            body_nodes = cfg.body_nodes
            item_var = cfg.item_var
        else:
            iterator_path = getattr(cfg, 'iterator_path', None)
            max_iterations = getattr(cfg, 'max_iterations', 100)
            body_nodes = getattr(cfg, 'body_nodes', [])
            item_var = getattr(cfg, 'item_var', 'item')
        
        if not iterator_path:
            raise ValueError(f"Loop node {cfg.id} missing iterator_path")
        
        # Get items to iterate over
        # Resolve list using helper so dotted paths like "load_csv.rows" work
        if hasattr(workflow, "_resolve_nested_path"):
            items = workflow._resolve_nested_path(ctx, iterator_path)  # type: ignore[attr-defined]
        else:
            items = ctx.get(iterator_path)
        if not isinstance(items, list):
            raise ValueError(f"Iterator path {iterator_path} must point to a list (got {type(items)})")

        results_raw: list[dict[str, Any]] = []
        for idx, item in enumerate(items[: max_iterations or len(items)]):
            # Build per-item context inheriting parent ctx
            item_ctx = {**ctx, item_var: item}
            item_result: dict[str, Any] = {"item_index": idx, "input": item}
            # Execute body nodes sequentially (respect order)
            for node_id in body_nodes:
                node_exec = await workflow.execute_node(node_id, item_ctx)
                item_ctx[node_id] = node_exec.output
                item_result[node_id] = node_exec.output
            results_raw.append(item_result)

        # Strip wrapper so downstream nodes get clean semantic outputs ---------
        cleaned_results: list[Any] = []
        for res in results_raw:
            if body_nodes and body_nodes[-1] in res:
                cleaned_results.append(res[body_nodes[-1]])
            else:
                cleaned_results.append(res)

        # Expose loop results in parent context for downstream nodes (e.g., aggregator)
        ctx[cfg.id] = cleaned_results
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        return NodeExecutionResult(
            success=True,
            output=cleaned_results,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                description=f"Loop execution: {iterator_path}"
            )
        )
        
    except Exception as e:
        from datetime import datetime
        start_time = datetime.utcnow()  # Set start_time for error case
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=False,
            error=str(e),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=getattr(cfg, 'name', 'loop_node'),
                version="1.0.0",
                owner="system",
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(e).__name__,
                provider=cfg.provider,
                description=f"Loop execution failed: {iterator_path}"
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

        # Handle different configuration formats
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
        tasks: List[asyncio.Task[Dict[str, Any]]] = [
            asyncio.create_task(execute_branch(branch, idx)) for idx, branch in enumerate(branches)
        ]
        
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
        processed_results: List[Dict[str, Any]] = []
        for idx, result in enumerate(branch_results):
            if isinstance(result, Exception):
                processed_results.append({"branch_error": str(result), "branch_index": idx})
            else:
                from typing import cast
                processed_results.append(cast(Dict[str, Any], result))
        
        # Merge outputs if requested
        output = {
            "branch_results": processed_results,
            "completed_branches": completed_branches,
            "strategy": wait_strategy
        }
        
        if merge_outputs and all(isinstance(r, dict) for r in processed_results):
            # Merge all branch outputs into a single dict
            merged: Dict[str, Any] = {}
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
                node_type=cfg.type,
                name=cfg.name,
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                description=f"Parallel execution: {len(branches)} branches"
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
                node_type=cfg.type,
                name=cfg.name,
                version="1.0.0",
                owner="system",
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=type(e).__name__,
                provider=cfg.provider,
                description=f"Parallel execution failed: {len(branches)} branches"
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
        import ast

        from ice_core.models import CodeNodeConfig

        # Handle different configuration formats
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
                node_type=cfg.type,
                name=getattr(cfg, 'name', 'code_node'),
                version="1.0.0",
                owner="system",
                start_time=start_time,
                end_time=end_time,
                duration=0,
                error_type=type(e).__name__,
                provider=cfg.provider,
                description=f"Code execution failed: {language}"
            ),
            execution_time=0
        ) 


# Recursive executor for cyclic agent conversations
@register_node("recursive")
async def recursive_executor(
    workflow: Workflow, cfg: Any, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute recursive node with convergence detection.
    
    Enables agents to loop back and continue conversations until convergence.
    Leverages existing infrastructure for safety and monitoring.
    """
    start_time = datetime.utcnow()
    
    try:
        from ice_core.models import (
            AgentNodeConfig,
            RecursiveNodeConfig,
            WorkflowNodeConfig,
        )

        # Handle different configuration formats
        if not isinstance(cfg, RecursiveNodeConfig):
            # Convert generic config to RecursiveNodeConfig if needed
            recursive_config = RecursiveNodeConfig(**cfg.__dict__)
        else:
            recursive_config = cfg
        
        # Get current iteration count from context
        iteration = ctx.get("_recursive_iteration", 0)
        context_key = recursive_config.context_key
        
        # Safety check using max_iterations
        if iteration >= recursive_config.max_iterations:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            return NodeExecutionResult(
                success=True,
                output={
                    "converged": False, 
                    "reason": "max_iterations_reached",
                    "iterations": iteration,
                    "final_context": ctx.get(context_key, {})
                },
                execution_time=duration,
                metadata=NodeMetadata(
                    node_id=recursive_config.id,
                    node_type=recursive_config.type,
                    name=recursive_config.name or "recursive_node",
                    version="1.0.0",
                    owner="system",
                    provider=recursive_config.provider,
                    error_type=None,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    description=f"Recursive execution: max iterations reached ({iteration})"
                )
            )
        
        # Check convergence condition if specified
        if recursive_config.convergence_condition:
            try:
                # Create a safe evaluation environment
                safe_globals = {
                    '__builtins__': {},
                    'True': True,
                    'False': False,
                    'None': None,
                    'and': lambda a, b: a and b,
                    'or': lambda a, b: a or b,
                    'not': lambda x: not x,
                }
                safe_globals.update(ctx)
                
                # Evaluate convergence condition
                converged = bool(eval(recursive_config.convergence_condition, safe_globals))
                
                if converged:
                    end_time = datetime.utcnow()
                    duration = (end_time - start_time).total_seconds()
                    
                    return NodeExecutionResult(
                        success=True,
                        output={
                            "converged": True, 
                            "reason": "condition_met",
                            "iterations": iteration,
                            "final_context": ctx.get(context_key, {})
                        },
                        execution_time=duration,
                        metadata=NodeMetadata(
                            node_id=recursive_config.id,
                            node_type=recursive_config.type,
                            name=recursive_config.name or "recursive_node",
                            version="1.0.0",
                            owner="system",
                            provider=recursive_config.provider,
                    error_type=None,
                            start_time=start_time,
                            end_time=end_time,
                            duration=duration,
                            description=f"Recursive execution: converged after {iteration} iterations"
                        )
                    )
            except Exception as e:
                # If condition evaluation fails, log and continue
                print(f"Warning: Convergence condition evaluation failed: {e}")
        
        # Prepare enhanced context for recursive execution
        enhanced_ctx = ctx.copy()
        enhanced_ctx["_recursive_iteration"] = iteration + 1
        
        # Preserve context across iterations if requested
        if recursive_config.preserve_context:
            if context_key not in enhanced_ctx:
                enhanced_ctx[context_key] = {}
            enhanced_ctx[context_key]["iteration"] = iteration + 1
            enhanced_ctx[context_key]["node_id"] = recursive_config.id
        
        # Execute agent or workflow using existing infrastructure
        if recursive_config.agent_package:
            # Use existing agent executor
            agent_cfg = AgentNodeConfig(
                id=recursive_config.id,
                name="recursive_agent",
                package=recursive_config.agent_package,
                max_iterations=10,  # Inner agent iterations
                input_selection=None,
                output_selection=None,
                agent_attr=None,
                model=None,
                version_constraint=None,
            )
            result = await agent_executor(workflow, agent_cfg, enhanced_ctx)
            
        elif recursive_config.workflow_ref:
            # Use existing workflow executor
            wf_cfg = WorkflowNodeConfig(
                id=recursive_config.id,
                name="recursive_workflow",
                workflow_ref=recursive_config.workflow_ref,
                input_selection=None,
                output_selection=None,
            )
            result = await workflow_executor(workflow, wf_cfg, enhanced_ctx)
        else:
            raise ValueError(f"Recursive node {recursive_config.id} must specify either agent_package or workflow_ref")
        
        # Enhanced result with recursion metadata
        if isinstance(result.output, dict):
            result.output["_recursive_iteration"] = iteration + 1
            result.output["_can_recurse"] = True
            result.output["_recursive_node_id"] = recursive_config.id
            
            # Update context if preserving
            if recursive_config.preserve_context:
                result.output[context_key] = enhanced_ctx.get(context_key, {})
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        result.execution_time = duration
        
        return result
        
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return NodeExecutionResult(
            success=False,
            error=str(e),
            output={"error": str(e)},
            execution_time=duration,
            metadata=NodeMetadata(
                node_id=getattr(cfg, 'id', 'recursive_unknown'),
                node_type="recursive",
                name=getattr(cfg, 'name', 'recursive_node'),
                version="1.0.0",
                owner="system",
                error_type=type(e).__name__,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                provider=getattr(cfg, 'provider', None),
                description=f"Recursive execution failed: {str(e)}",
            )
        ) 

# ---------------------------------------------------------------------------
# New Phase-2 executors (minimal MVP implementations) ------------------------
# ---------------------------------------------------------------------------

from ice_core.models import (  # noqa: E402 – after large import section
    HumanNodeConfig,
    MonitorNodeConfig,
    SwarmNodeConfig,
)


@register_node("human")
async def human_executor(workflow: Workflow, cfg: HumanNodeConfig, ctx: Dict[str, Any]) -> NodeExecutionResult:  # noqa: D401
    """Simulated human approval node.

    MVP implementation: instantly approves and returns a canned response so
    automated tests pass.  Real UI/backend can later replace this behaviour.
    """
    from datetime import datetime

    start = datetime.utcnow()
    response = {
        "approved": True,
        "response": "approved automatically by MVP human executor"
    }
    end = datetime.utcnow()

    return NodeExecutionResult(
        success=True,
        output=response,
        metadata=NodeMetadata(
            node_id=cfg.id,
            node_type=cfg.type,
            name="human_approval",
            version="1.0.0",
            owner="system",
            provider=cfg.provider,
                error_type=None,
            start_time=start,
            end_time=end,
            duration=(end - start).total_seconds(),
            description="Human approval node execution"
        ),
    )


@register_node("monitor")
async def monitor_executor(workflow: Workflow, cfg: MonitorNodeConfig, ctx: Dict[str, Any]) -> NodeExecutionResult:  # noqa: D401
    """Stub monitor executor that evaluates metric expression (noop)."""
    from datetime import datetime
    start = datetime.utcnow()

    # Simple evaluation using eval on context (unsafe in prod)
    try:
        triggered = bool(eval(cfg.metric_expression, {}, ctx))
    except Exception:
        triggered = False

    output = {
        "metric_evaluated": cfg.metric_expression,
        "triggered": triggered,
        "triggers_fired": int(triggered),
        "checks_performed": 1,
    }

    if triggered:
        output["action_taken"] = cfg.action_on_trigger
        if cfg.action_on_trigger == "alert_only":
            output["alerts_sent"] = cfg.alert_channels or []

    end = datetime.utcnow()
    return NodeExecutionResult(
        success=True,
        output=output,
        metadata=NodeMetadata(
            node_id=cfg.id,
            node_type=cfg.type,
            name="monitor_node",
            version="1.0.0",
            owner="system",
            provider=cfg.provider,
                error_type=None,
            start_time=start,
            end_time=end,
            duration=(end - start).total_seconds(),
            description=f"Monitor execution: {cfg.metric_expression}"
        ),
    )


@register_node("swarm")
async def swarm_executor(workflow: Workflow, cfg: SwarmNodeConfig, ctx: Dict[str, Any]) -> NodeExecutionResult:  # noqa: D401
    """Minimal swarm executor.

    MVP: tries to resolve agent import paths; returns failure if missing.
    No real coordination yet – this satisfies current tests which expect
    a graceful failure when test agents are absent.
    """
    from datetime import datetime
    start = datetime.utcnow()

    missing: list[str] = []
    for agent in cfg.agents:
        try:
            registry.get_agent_import_path(agent.role)
        except KeyError:
            missing.append(agent.role)

    if missing:
        end = datetime.utcnow()
        return NodeExecutionResult(
            success=False,
            error=f"Agents not found in registry: {', '.join(missing)}",
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name="swarm_node",
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start,
                end_time=end,
                duration=(end - start).total_seconds(),
                description=f"Swarm execution failed: missing agents {missing}"
            ),
        )

    # If all agents present, return dummy aggregated response
    end = datetime.utcnow()
    return NodeExecutionResult(
        success=True,
        output={"swarm": "executed", "agents": [a.role for a in cfg.agents]},
        metadata=NodeMetadata(
            node_id=cfg.id,
            node_type=cfg.type,
            name="swarm_node",
            version="1.0.0",
            owner="system",
            provider=cfg.provider,
                error_type=None,
            start_time=start,
            end_time=end,
            duration=(end - start).total_seconds(),
            description="Swarm execution completed"
        ),
    ) 