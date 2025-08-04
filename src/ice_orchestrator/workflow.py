"""Core workflow execution engine for iceOS.

WHY THIS MODULE EXISTS:
- This is the "Runtime Tier" of the 3-tier architecture
- Executes validated blueprints from the MCP tier with guarantees
- Handles all runtime concerns: retries, caching, error recovery
- Provides deterministic execution with full observability

ARCHITECTURAL CONTEXT:
- Receives: Validated blueprints (from MCP tier)
- Executes: Via NodeExecutor with proper error handling
- Returns: Detailed execution results with costs and telemetry
- Future: Will provide optimization hints back to Frosty

KEY RESPONSIBILITIES:
1. DAG-based execution with proper dependency resolution
2. Context propagation between nodes
3. Cost tracking and budget enforcement
4. Event streaming for real-time updates
5. Graceful degradation and error recovery

This is intentionally complex because it handles ALL runtime concerns
so that the blueprint layer can remain pure and focused on validation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast

import structlog
from opentelemetry import trace  # type: ignore[import-not-found]
from opentelemetry.trace import Status, StatusCode  # type: ignore[import-not-found]

from ice_core.base_tool import ToolBase
from ice_core.graph.dependency_graph import DependencyGraph
from ice_core.graph.level_resolver import BranchGatingResolver
from ice_core.models import (
    ChainExecutionResult,
    ConditionNodeConfig,
    NodeConfig,
    NodeExecutionResult,
    WorkflowNodeConfig,
)
from ice_core.models.node_models import NodeMetadata
from ice_core.utils.perf import WeightedSemaphore, estimate_complexity
from ice_core.validation import SafetyValidator, SchemaValidator

# NOTE: use AgentNode from SDK to avoid core dependency
from ice_orchestrator.agent import AgentNode
from ice_orchestrator.base_workflow import BaseWorkflow, FailurePolicy
from ice_orchestrator.config import runtime_config
from ice_orchestrator.context import GraphContextManager
from ice_orchestrator.execution.cost_estimator import WorkflowCostEstimator

# Use WorkflowBuilder for creating workflows
from ice_orchestrator.execution.executor import NodeExecutor
from ice_orchestrator.execution.metrics import ChainMetrics
from ice_orchestrator.execution.workflow_events import (
    NodeCompleted,
    NodeFailed,
    NodeStarted,
    WorkflowCompleted,
    WorkflowEventHandler,
    WorkflowStarted,
)
from ice_orchestrator.execution.workflow_state import (
    ExecutionPhase,
    WorkflowExecutionState,
)
from ice_orchestrator.utils.context_builder import ContextBuilder
from ice_orchestrator.validation.chain_validator import ChainValidator
from ice_orchestrator.workflow_execution_context import WorkflowExecutionContext

# ---------------------------------------------------------------------------
# Tracing & logging setup ----------------------------------------------------
# ---------------------------------------------------------------------------
tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)

class Workflow(BaseWorkflow):  # type: ignore[misc]  # mypy cannot resolve BaseScriptChain across namespace package boundary
    """Execute a directed acyclic workflow using level-based parallelism.

    This is the core execution engine that drives all iceOS workflows,
    from simple task chains to complex spatial computing orchestrations.

    Features:
    - Level-based parallel execution with intelligent scheduling
    - Graph analysis and spatial reasoning capabilities  
    - Robust error handling with configurable policies
    - Real-time event streaming and monitoring
    - Context & state management with dependency tracking
    - Performance features (caching, large output handling)
    - Advanced observability (metrics, tracing, callbacks)
    - Canvas-ready spatial layout intelligence
    """

    def __init__(
        self,
        nodes: List[NodeConfig],
        name: Optional[str] = None,
        *,
        version: str = "1.0.0",
        context_manager: Optional[GraphContextManager] = None,
        callbacks: Optional[List[Any]] = None,
        max_parallel: int = 5,
        persist_intermediate_outputs: bool = True,
        tools: Optional[List[ToolBase]] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[WorkflowExecutionContext] = None,
        chain_id: Optional[str] = None,
        failure_policy: FailurePolicy = FailurePolicy.CONTINUE_POSSIBLE,
        validate_outputs: bool = True,
        token_ceiling: int | None = None,
        depth_ceiling: int | None = None,
        token_guard: Any | None = None,
        depth_guard: Any | None = None,
        session_id: Optional[str] = None,
        use_cache: bool = True,
    ) -> None:
        """Initialize Workflow.

        Args:
            nodes: List of node configurations
            name: Engine instance name
            version: Engine version
            context_manager: Context manager
            callbacks: List of callbacks
            max_parallel: Maximum parallel executions
            persist_intermediate_outputs: Whether to persist outputs
            tools: List of tools available to nodes
            initial_context: Initial execution context
            workflow_context: Workflow execution context
            chain_id: Unique engine identifier
            failure_policy: Failure handling policy
            validate_outputs: Whether to validate node outputs
            token_ceiling: Token ceiling for execution
            depth_ceiling: Depth ceiling for execution
            token_guard: Token guard for execution
            depth_guard: Depth guard for execution
            session_id: Session identifier
            use_cache: Engine-level cache toggle
        """
        self.chain_id = chain_id or f"wf_{datetime.utcnow().isoformat()}"
        # Semantic version for migration tracking -----------------------
        self.version: str = version

        # Blueprint layer: Auto-populate schemas for tool nodes BEFORE validation
        nodes = self._populate_missing_schemas(nodes)

        # Safety checks BEFORE super().__init__ builds runtime structures ----
        SafetyValidator.validate_layer_boundaries()
        SafetyValidator.validate_node_tool_access(nodes)

        # Ensure _chain_tools is set before any use
        self._chain_tools = tools or []

        super().__init__(
            nodes,
            name,
            context_manager,
            callbacks,
            max_parallel,
            persist_intermediate_outputs,
            tools,
            initial_context,
            workflow_context,
            failure_policy,
            session_id=session_id,
            use_cache=use_cache,
        )
        self.validate_outputs = validate_outputs
        self.use_cache = use_cache
        self.token_ceiling = token_ceiling or runtime_config.max_tokens
        self.depth_ceiling = depth_ceiling or runtime_config.max_depth
        # External guard callbacks --------------------------------------
        self._token_guard = token_guard
        self._depth_guard = depth_guard

        # Build dependency graph
        self.graph = DependencyGraph(nodes)
        self.graph.validate_schema_alignment(nodes)
        self.levels = self.graph.get_level_nodes()

        # Track decisions made by *condition* nodes - must be after graph building
        self._branch_resolver = BranchGatingResolver(self.nodes, self.graph)
        
        # Preserve original attrs for B/C (alias to resolver internals)
        self._branch_decisions = self._branch_resolver.branch_decisions  # type: ignore[attr-defined]
        self._active_cache = self._branch_resolver.active_cache  # type: ignore[attr-defined]

        # Validator helper ----------------------------------------------------
        self._validator = ChainValidator(self.failure_policy, self.levels, self.nodes)

        # Metrics & events
        self.metrics = ChainMetrics()
        # Executor helper -----------------------------------------------------
        self._executor = NodeExecutor(self)
        # LLM nodes are now direct API calls
        # Schema validator helper ---------------------------------------------
        self._schema_validator = SchemaValidator()

        from ice_core.cache import global_cache  # local import to avoid cycles

        self._cache = global_cache()

        # Log initialization
        logger.info(
            "Initialized Workflow with %d nodes across %d levels",
            len(nodes),
            len(self.levels),
        )
        
        # New components for enhanced functionality
        self._event_handler = WorkflowEventHandler()
        self._cost_estimator: WorkflowCostEstimator = WorkflowCostEstimator()  # type: ignore[no-untyped-call]
        self._execution_state: Optional[WorkflowExecutionState] = None
        
        # Graph intelligence analyzer
        from ice_orchestrator.context.graph_analyzer import GraphAnalyzer
        self._graph_analyzer = GraphAnalyzer(self.graph.graph)  # Use the NetworkX graph from DependencyGraph

        # Agent instance cache
        self._agent_cache: Dict[str, AgentNode] = {}

        # 🚀 Enhanced NetworkX integration - Track execution with rich analytics
        self._execution_start_times: Dict[str, float] = {}
        self._optimization_insights_enabled = True

    def _populate_missing_schemas(self, nodes: List[NodeConfig]) -> List[NodeConfig]:
        """Blueprint layer: Auto-populate schemas for tool nodes.
        
        This is the critical bridge that makes the blueprint layer seamless -
        it automatically discovers and populates schemas from registered tools
        so users don't have to manually specify them.
        """
        from ice_core.models.node_models import ToolNodeConfig
        from ice_core.utils.node_conversion import populate_tool_node_schemas
        
        updated_nodes: List[NodeConfig] = []
        for node in nodes:
            if isinstance(node, ToolNodeConfig):
                # Auto-populate schemas from registered tool
                updated_node = populate_tool_node_schemas(node)
                updated_nodes.append(updated_node)
            else:
                # Non-tool nodes pass through unchanged
                updated_nodes.append(node)
        
        return updated_nodes

    async def execute(self) -> NodeExecutionResult:
        """Execute the workflow and return a ChainExecutionResult."""
        start_time = datetime.utcnow()
        results: Dict[str, NodeExecutionResult] = {}
        errors: List[str] = []

        logger.info(
            "Starting execution of workflow '%s' (ID: %s)", self.name, self.chain_id
        )

        with tracer.start_as_current_span(
            "workflow.execute",
            attributes={
                "chain_id": self.chain_id,
                "workflow_name": self.name,
                "node_count": len(self.nodes),
            },
        ) as chain_span:
            for level_idx, level_num in enumerate(sorted(self.levels.keys()), start=1):
                # External depth guard takes priority --------------------
                if self._depth_guard and not self._depth_guard(
                    level_idx, self.depth_ceiling
                ):
                    errors.append("Depth guard aborted execution")
                    break

                if self.depth_ceiling is not None and level_idx > self.depth_ceiling:
                    logger.warning(
                        "Depth ceiling reached (%s); aborting further levels.",
                        self.depth_ceiling,
                    )
                    errors.append("Depth ceiling reached")
                    break

                level_node_ids = self.levels[level_num]
                # Filter nodes by branch decisions (condition gating) -----
                active_node_ids = [
                    nid for nid in level_node_ids if self._is_node_active(nid)
                ]
                level_nodes = [self.nodes[node_id] for node_id in active_node_ids]

                level_results = await self._execute_level(level_nodes, results)

                for node_id, result in level_results.items():
                    results[node_id] = result

                    if result.success:
                        if hasattr(result, "usage") and result.usage:
                            self.metrics.update(node_id, result)

                            # External token guard hook -------------------
                            if self._token_guard and not self._token_guard(
                                self.metrics.total_tokens, self.token_ceiling
                            ):
                                errors.append("Token guard aborted execution")
                                break

                            # Token ceiling enforcement ----------------------
                            if (
                                self.token_ceiling is not None
                                and self.metrics.total_tokens > self.token_ceiling
                            ):
                                                            logger.warning(
                                "Token ceiling exceeded (%s); aborting workflow.",
                                self.token_ceiling,
                            )
                            errors.append("Token ceiling exceeded")
                            break

                    # ----------------------------------------------------------------------
                    # Record branch decision for *condition* nodes (always, not usage-only)
                    # ----------------------------------------------------------------------
                    node_cfg = self.nodes[node_id]
                    if (
                        isinstance(node_cfg, ConditionNodeConfig)
                        and isinstance(result.output, dict)
                        and "result" in result.output
                    ):
                        try:
                            self._branch_resolver.record_decision(
                                node_id, bool(result.output["result"])
                            )
                        except Exception:
                            # Defensive fallback – ignore unexpected conversion issues
                            pass

                    # When the node execution failed, collect error information
                    if not result.success:
                        errors.append(f"Node {node_id} failed: {result.error}")

                if errors and not self._validator.should_continue(errors):
                    break

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            logger.info(
                "Completed workflow execution",
                workflow=self.name,
                chain_id=self.chain_id,
                duration=duration,
            )

            chain_span.set_attribute("success", len(errors) == 0)
            if errors:
                chain_span.set_status(Status(StatusCode.ERROR, ";".join(errors)))
            chain_span.end()

        final_node_id = self.graph.get_leaf_nodes()[0]

        # Extract only the output fields from NodeExecutionResult objects for JSON serialization
        serializable_results = {}
        for node_id, result in results.items():
            if result.success and result.output is not None:
                serializable_results[node_id] = result.output
            else:
                # For failed nodes, include error information
                serializable_results[node_id] = {
                    "success": False,
                    "error": result.error or "Unknown error"
                }
        
        # Wrap ChainExecutionResult as NodeExecutionResult for ABC compliance
        chain_result = ChainExecutionResult(
            success=len(errors) == 0,
            output=serializable_results,
            error="\n".join(errors) if errors else None,
            metadata=NodeMetadata(
                node_id=final_node_id,
                node_type="workflow",
                name=self.name,
                version="1.0.0",
                start_time=start_time,
                end_time=end_time,
                duration=duration,
            ),  # type: ignore[call-arg]
            chain_metadata=getattr(self, "metadata", None),
            execution_time=duration,
            token_stats=self.metrics.as_dict(),
        )
        return NodeExecutionResult(
            success=chain_result.success,
            error=chain_result.error,
            output=chain_result.output,
            metadata=chain_result.metadata,
            usage=None,
            execution_time=chain_result.execution_time,
            context_used=None,
            token_stats=chain_result.token_stats,
            budget_status=None,
        )

    async def _execute_level(
        self,
        level_nodes: List[NodeConfig],
        accumulated_results: Dict[str, NodeExecutionResult],
    ) -> Dict[str, NodeExecutionResult]:
        """Execute all processors at a given level in parallel."""
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def process_node(node: NodeConfig) -> Tuple[str, NodeExecutionResult]:
            weight = max(1, estimate_complexity(node))
            async with WeightedSemaphore(semaphore, weight):
                result = await self.execute_node(
                    node.id,
                    self._build_node_context(node, accumulated_results),
                )
                return node.id, result

            # The context manager above always returns; this line is never
            # reached but satisfies static analysis that a return statement
            # exists on all code paths (mypy + pyright).
            raise RuntimeError("unreachable")  # pragma: no cover

        tasks = [process_node(node) for node in level_nodes]
        # Gather with *return_exceptions* so that a single processor failure does not
        # crash the entire level when *failure_policy* allows continuation.  Any
        # exception is immediately converted into a failed *NodeExecutionResult*
        # so downstream bookkeeping remains consistent.
        gathered = await asyncio.gather(*tasks, return_exceptions=True)

        level_results: Dict[str, NodeExecutionResult] = {}
        for item in gathered:
            if isinstance(item, tuple) and len(item) == 2:
                node_id, result_or_exc = item

                if isinstance(result_or_exc, Exception):
                    # Convert the exception into a generic failure result so the
                    # orchestrator can apply failure policies without blowing up.
                    from datetime import datetime

                    from ice_core.models.node_models import (
                        NodeExecutionResult,
                        NodeMetadata,
                    )

                    failure_meta = NodeMetadata(  # type: ignore[call-arg]
                        node_id=node_id,
                        node_type="unknown",
                        name=node_id,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        duration=0.0,
                        error_type=type(result_or_exc).__name__,
                    )

                    level_results[node_id] = NodeExecutionResult(  # type: ignore[call-arg]
                        success=False,
                        error=str(result_or_exc),
                        metadata=failure_meta,
                    )
                else:
                    level_results[node_id] = result_or_exc
            else:
                # Defensive branch — should not happen but avoid silent loss.
                import reprlib
                from datetime import datetime

                from ice_core.models.node_models import (
                    NodeExecutionResult,
                    NodeMetadata,
                )

                node_id = "unknown" if not item else str(item)
                level_results[node_id] = NodeExecutionResult(  # type: ignore[call-arg]
                    success=False,
                    error=f"Unexpected gather payload: {reprlib.repr(item)}",
                    metadata=NodeMetadata(  # type: ignore[call-arg]
                        node_id=node_id,
                        node_type="unknown",
                        name=node_id,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        duration=0.0,
                        error_type="GatherPayloadError",
                    ),
                )
        
        # NEW: Handle recursive flows
        await self._handle_recursive_flows(level_results, accumulated_results)
        
        return level_results

    async def _handle_recursive_flows(
        self, 
        level_results: Dict[str, NodeExecutionResult], 
        accumulated_results: Dict[str, NodeExecutionResult]
    ) -> None:
        """Handle recursive flows by scheduling recursive execution when needed."""
        
        recursive_executions = []
        
        for node_id, result in level_results.items():
            node = self.nodes.get(node_id)
            
            # Check if this is a recursive node that needs to continue
            if (node and hasattr(node, 'type') and node.type == 'recursive' and
                isinstance(result.output, dict) and 
                result.output.get("_can_recurse", False) and 
                not result.output.get("converged", False)):
                
                # Get recursive sources from the node configuration
                recursive_sources = getattr(node, 'recursive_sources', [])
                
                # Schedule recursive execution for each source
                for source_id in recursive_sources:
                    if source_id in self.nodes:
                        recursive_executions.append((source_id, result.output))
        
        # Execute recursive flows
        for source_id, recursive_context in recursive_executions:
            await self._execute_recursive_node(source_id, recursive_context, accumulated_results)
    
    async def _execute_recursive_node(
        self, 
        node_id: str, 
        recursive_context: Dict[str, Any], 
        accumulated_results: Dict[str, NodeExecutionResult]
    ) -> None:
        """Execute a single node in a recursive context."""
        
        try:
            node = self.nodes[node_id]
            
            # Build enhanced context for recursive execution
            base_context = self._build_node_context(node, accumulated_results)
            
            # Merge recursive context
            enhanced_context = {**base_context, **recursive_context}
            
            # Execute the node with recursive context
            result = await self.execute_node(node_id, enhanced_context)
            
            # Update accumulated results for next iteration
            accumulated_results[node_id] = result
            
            # If this node can also recurse, handle it
            if (hasattr(node, 'type') and node.type == 'recursive' and
                isinstance(result.output, dict) and 
                result.output.get("_can_recurse", False) and 
                not result.output.get("converged", False)):
                
                # Continue the recursive chain
                await self._handle_recursive_flows({node_id: result}, accumulated_results)
                
        except Exception as e:
            logger.error(f"Error in recursive execution for node {node_id}: {e}")
            # Create error result
            from datetime import datetime

            from ice_core.models.node_models import NodeExecutionResult, NodeMetadata
            
            error_result = NodeExecutionResult(
                success=False,
                error=str(e),
                output=None,
                metadata=NodeMetadata(
                    node_id=node_id,
                    node_type="recursive",
                    name=node_id,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    duration=0.0,
                    error_type=type(e).__name__,
                    version="1.0.0",
                    owner="system",
                    description=f"Recursive node execution error for {node_id}",
                    provider=None
                )
            )
            accumulated_results[node_id] = error_result

    def _build_node_context(
        self,
        node: NodeConfig,
        accumulated_results: Dict[str, NodeExecutionResult],
    ) -> Dict[str, Any]:
        """Compose processor input context.

        1. Start with ContextBuilder-derived inputs (dependencies & mappings).
        2. Merge **session metadata** from the active GraphContext so that
           root-level placeholders like ``{tone}`` are resolvable without the
           boilerplate of explicit ``input_mappings``.  Chain-level metadata
           always takes *lower* precedence so explicit mappings win when keys
           collide.
        """

        node_ctx = ContextBuilder.build_node_context(node, accumulated_results)

        # ------------------------------------------------------------------
        # Expose **dependency outputs** directly under their node IDs so that
        # Jinja templates can reference e.g. ``{{kb_lookup.context}}`` without
        # explicit InputMappings on every consumer node.
        # ------------------------------------------------------------------

        for dep_id in getattr(node, "dependencies", []):
            dep_result = accumulated_results.get(dep_id)
            if dep_result and dep_result.success and dep_result.output is not None:
                # Prefer not to overwrite when the context already has a key
                # (explicit mappings > implicit exposure).
                # Store only the output, not the entire NodeExecutionResult
                node_ctx.setdefault(dep_id, dep_result.output)

        # Inject high-level metadata provided via ``chain.context_manager`` so
        # that first-level nodes can access user inputs (e.g. tone, guardrails)
        # without needing dummy upstream nodes.
        try:
            current_ctx = self.context_manager.get_context()
            if current_ctx and current_ctx.metadata:
                # Preserve explicit mappings when keys overlap ----------------
                merged = {**current_ctx.metadata, **node_ctx}
                return merged
        except Exception:  # – never break execution due to ctx issues
            pass

        return node_ctx

    @staticmethod
    def _resolve_nested_path(data: Any, path: str) -> Any:
        """Delegate to :class:`ContextBuilder`."""

        return ContextBuilder.resolve_nested_path(data, path)  # type: ignore[return-value]  # dynamic path resolution returns Any

    def _lookup_node_result(self, node_id: str) -> Optional[NodeExecutionResult]:
        """Fetch a node's execution result irrespective of NodeType grouping."""
        if not self._execution_state:
            return None
        for type_results in self._execution_state.node_results.values():
            if node_id in type_results:
                return type_results[node_id]
        return None

    # ---------------------------------------------------------------------
    # Graph inspection public API -----------------------------------------
    # ---------------------------------------------------------------------

    def get_node_dependencies(self, node_id: str) -> List[str]:
        """Get dependencies for a processor."""
        return self.graph.get_node_dependencies(node_id)

    def get_node_dependents(self, node_id: str) -> List[str]:
        """Get dependents for a processor."""
        return self.graph.get_node_dependents(node_id)

    def get_node_level(self, node_id: str) -> int:
        """Get execution level for a processor."""
        return self.graph.get_node_level(node_id)

    def get_level_nodes(self, level: int) -> List[str]:
        """Get processors at a specific level."""
        return self.levels.get(level, [])

    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics."""
        return self.metrics.as_dict()
    
    # ---------------------------------------------------------------------
    # Enhanced execution methods for canvas/streaming -----------------------
    # ---------------------------------------------------------------------
    
    async def execute_with_events(
        self,
        event_callback: Optional[Any] = None,
        checkpoint_interval: Optional[int] = None
    ) -> NodeExecutionResult:
        """Execute workflow with event streaming for real-time monitoring.
        
        Args:
            event_callback: Async function to receive events
            checkpoint_interval: Save state every N nodes (for recovery)
            
        Returns:
            Standard execution result
        """
        # Initialize execution state
        self._execution_state = WorkflowExecutionState(
            workflow_id=self.chain_id,
            workflow_name=self.name or "unnamed",
            checkpoint_enabled=checkpoint_interval is not None
        )
        
        # Subscribe callback if provided
        if event_callback:
            self._event_handler.subscribe_all(event_callback)
            
        # Emit workflow started event
        await self._event_handler.emit(WorkflowStarted(
            workflow_id=self.chain_id,
            workflow_name=self.name or "unnamed",
            total_nodes=len(self.nodes),
            total_levels=len(self.levels),
            estimated_cost=self.estimate_cost().total_avg_cost,
            estimated_duration_seconds=self.estimate_cost().duration_estimate_seconds
        ))
        
        try:
            # Use regular execute but with state tracking
            self._execution_state.phase = ExecutionPhase.EXECUTING
            result = await self.execute()
            
            # Emit completion event
            self._execution_state.phase = ExecutionPhase.COMPLETED
            self._execution_state.end_time = datetime.utcnow()
            
            await self._event_handler.emit(WorkflowCompleted(
                workflow_id=self.chain_id,
                duration_seconds=(self._execution_state.end_time - self._execution_state.start_time).total_seconds(),
                total_tokens=self._execution_state.total_tokens,
                total_cost=self._execution_state.total_cost,
                nodes_executed=len(self._execution_state.completed_nodes),
                nodes_skipped=len(self._execution_state.skipped_nodes)
            ))
            
            return result
        except Exception as e:
            # Emit failure event
            self._execution_state.phase = ExecutionPhase.FAILED
            self._execution_state.end_time = datetime.utcnow()
            
            await self._event_handler.emit(WorkflowCompleted(
                workflow_id=self.chain_id,
                duration_seconds=(self._execution_state.end_time - self._execution_state.start_time).total_seconds(),
                total_tokens=self._execution_state.total_tokens,
                total_cost=self._execution_state.total_cost,
                nodes_executed=len(self._execution_state.completed_nodes),
                nodes_skipped=len(self._execution_state.skipped_nodes),
                metadata={"error": str(e)}
            ))
            raise
    
    def get_debug_info(self, node_id: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive debug information for troubleshooting.
        
        Args:
            node_id: Specific node to debug, or None for workflow-level info
            
        Returns:
            Debug information including dependencies, context, and execution history
        """
        if node_id:
            return self._get_node_debug_info(node_id)
        else:
            return self._get_workflow_debug_info()
            
    def _get_node_debug_info(self, node_id: str) -> Dict[str, Any]:
        """Get debug info for a specific node."""
        node = self.nodes.get(node_id)
        if not node:
            return {"error": f"Node {node_id} not found"}
            
        debug_info = {
            "node_id": node_id,
            "node_type": node.type,
            "config": node.model_dump(),
            "dependencies": {
                "upstream": node.dependencies,
                "downstream": self.graph.get_node_dependents(node_id)
            },
            "level": self.graph.get_node_level(node_id),
            "validation": {
                "input_schema": getattr(node, 'input_schema', None),
                "output_schema": getattr(node, 'output_schema', None),
                "required_tools": getattr(node, 'tools', [])
            }
        }
        
        # Add execution info if available
        if self._execution_state:
            result = self._lookup_node_result(node_id)
            if result:
                debug_info["execution"] = {
                    "executed": node_id in self._execution_state.completed_nodes,
                    "success": result.success,
                    "error": result.error,
                    "duration": result.execution_time,
                    "output_preview": self._safe_preview(result.output),
                    "context_used": self._safe_preview(result.context_used)
                }
                
        # Add suggestions for common issues
        debug_info["diagnostics"] = self._diagnose_node_issues(node)
        
        return debug_info
        
    def _get_workflow_debug_info(self) -> Dict[str, Any]:
        """Get debug info for entire workflow."""
        debug_info = {
            "workflow_id": self.chain_id,
            "workflow_name": self.name,
            "total_nodes": len(self.nodes),
            "total_levels": len(self.levels),
            "node_breakdown": {},
            "execution_order": [],
            "validation_issues": self.validate_chain()
        }
        
        # Node type breakdown
        node_breakdown: Dict[str, int] = cast(Dict[str, int], debug_info["node_breakdown"])
        for node in self.nodes.values():
            node_type = node.type
            node_breakdown[node_type] = node_breakdown.get(node_type, 0) + 1
            
        # Execution order
        execution_order: List[Dict[str, Any]] = cast(List[Dict[str, Any]], debug_info["execution_order"])
        for level_num in sorted(self.levels.keys()):
            for node_id in self.levels[level_num]:
                execution_order.append({
                    "level": level_num,
                    "node_id": node_id,
                    "type": self.nodes[node_id].type
                })
                
        # Add execution summary if available
        if self._execution_state:
            debug_info["execution_summary"] = self._execution_state.get_execution_summary()
            
        return debug_info
        
    def _safe_preview(self, data: Any, max_length: int = 200) -> Any:
        """Create a safe preview of data for debugging."""
        if data is None:
            return None
        
        data_str = str(data)
        if len(data_str) > max_length:
            return data_str[:max_length] + "..."
        return data
        
    def _diagnose_node_issues(self, node: NodeConfig) -> List[str]:
        """Diagnose common node configuration issues."""
        issues = []
        
        # Check for missing dependencies
        for dep_id in node.dependencies:
            if dep_id not in self.nodes:
                issues.append(f"Missing dependency: {dep_id}")
                
        # Check schema compatibility
        if hasattr(node, 'input_schema') and node.input_schema:
            for dep_id in node.dependencies:
                dep_node = self.nodes.get(dep_id)
                if dep_node and hasattr(dep_node, 'output_schema'):
                    # Basic compatibility check
                    if not self._schemas_compatible(dep_node.output_schema, node.input_schema):
                        issues.append(f"Schema mismatch with dependency {dep_id}")
                        
        # Type-specific checks
        if node.type == "llm" and hasattr(node, 'model'):
            if "gpt-4" in node.model and hasattr(node, 'max_tokens'):
                if node.max_tokens is not None and node.max_tokens > 8000:
                    issues.append("max_tokens exceeds GPT-4 limit")
                    
        return issues
        
    def _schemas_compatible(self, output_schema: Any, input_schema: Any) -> bool:
        """Basic schema compatibility check."""
        # This is simplified - real implementation would be more thorough
        if isinstance(output_schema, dict) and isinstance(input_schema, dict):
            # Check if output keys satisfy input requirements
            output_keys = set(output_schema.keys())
            input_keys = set(input_schema.keys())
            return input_keys.issubset(output_keys)
        return True
            
    async def execute_incremental(
        self,
        up_to_node_id: Optional[str] = None,
        from_checkpoint: Optional[Dict[str, Any]] = None
    ) -> NodeExecutionResult:
        """Execute workflow incrementally for debugging or preview.
        
        Args:
            up_to_node_id: Stop after this node completes
            from_checkpoint: Resume from saved state
            
        Returns:
            Partial execution result
        """
        if from_checkpoint:
            self._execution_state = WorkflowExecutionState.from_checkpoint(from_checkpoint)
        else:
            self._execution_state = WorkflowExecutionState(
                workflow_id=self.chain_id,
                workflow_name=self.name or "unnamed"
            )
            
        # Incremental execution not yet implemented
        # For now, delegate to regular execute
        return await self.execute()
        
    def estimate_cost(self, context_size: int = 1000) -> Any:
        """Estimate execution cost before running.
        
        Args:
            context_size: Estimated context size in tokens
            
        Returns:
            WorkflowCostEstimate with breakdown by node
        """
        return self._cost_estimator.estimate_workflow_cost(
            list(self.nodes.values()),
            context_size
        )
        
    def suggest_next_nodes(self, after_node_id: str) -> List[Dict[str, Any]]:
        """Get AI suggestions for nodes that could follow the given node.
        
        This helps Frosty suggest next steps during canvas construction.
        Enhanced with graph intelligence for better suggestions.
        
        Args:
            after_node_id: Node to get suggestions after
            
        Returns:
            List of suggestions with reasoning
        """
        node = self.nodes.get(after_node_id)
        if not node:
            return []
            
        suggestions = []
        
        # Get graph-based insights
        impact_analysis = self.analyze_node_impact(after_node_id)
        graph_metrics = self.get_graph_metrics()
        
        # Analyze current node's position in graph
        current_level = self.get_node_level(after_node_id)
        out_degree = len(impact_analysis["direct_dependents"])
        
        # Enhanced suggestions based on graph analysis
        if hasattr(node, 'output_schema') and node.output_schema:
            if ((isinstance(node.output_schema, dict) and 'data' in node.output_schema) or 'array' in str(node.output_schema)):
                # Consider parallelization if we're not already branching heavily
                if out_degree < 2 and graph_metrics["parallel_opportunities"] < graph_metrics["total_nodes"] * 0.4:
                    suggestions.append({
                        "type": "parallel",
                        "reason": "Parallel processing opportunity - could split data processing",
                        "priority": "high",
                        "suggested_config": {
                            "type": "parallel",
                            "branches": [
                                {"type": "llm", "model": "gpt-3.5-turbo", "prompt": "Analyze: {data}"},
                                {"type": "tool", "tool_name": "data_validator", "validate": "{data}"}
                            ]
                        }
                    })
                else:
                    suggestions.append({
                        "type": "llm",
                        "reason": "Process or analyze the data output",
                        "priority": "medium",
                        "suggested_config": {
                            "type": "llm",
                            "model": "gpt-3.5-turbo",
                            "prompt": "Analyze the following data: {data}"
                        }
                    })
                    
            if ((isinstance(node.output_schema, dict) and 'text' in node.output_schema) or 'string' in str(node.output_schema)):
                suggestions.append({
                    "type": "tool",
                    "reason": "Take action based on the text output",
                    "priority": "medium",
                    "suggested_tools": ["email_sender", "slack_notifier", "file_writer"]
                })
                
        # Type-specific suggestions enhanced with graph context
        if node.type == "llm":
            # Check if we're creating a bottleneck
            if after_node_id in graph_metrics["bottleneck_nodes"]:
                suggestions.append({
                    "type": "condition",
                    "reason": "Add branching to reduce bottleneck at this LLM node",
                    "priority": "high",
                    "suggested_config": {
                        "type": "condition",
                        "condition": "result.confidence > 0.8"
                    }
                })
            else:
                suggestions.extend([
                    {
                        "type": "condition",
                        "reason": "Make decision based on LLM output",
                        "priority": "medium",
                        "suggested_config": {
                            "type": "condition",
                            "condition": "result.confidence > 0.8"
                        }
                    },
                    {
                        "type": "tool",
                        "reason": "Execute action based on analysis",
                        "priority": "medium",
                        "suggested_tools": ["database_writer", "api_caller"]
                    }
                ])
                
        elif node.type == "tool":
            # Check critical path position
            path_analysis = self.get_execution_path_analysis()
            if after_node_id in path_analysis.get("branch_points", []):
                suggestions.append({
                    "type": "parallel",
                    "reason": "Leverage branching opportunity from this tool output",
                    "priority": "high"
                })
            else:
                suggestions.append({
                    "type": "llm",
                    "reason": "Process tool output with AI",
                    "priority": "medium",
                    "suggested_config": {
                        "type": "llm",
                        "model": "gpt-3.5-turbo",
                        "prompt": "Summarize this result: {output}"
                    }
                })
                
        # Add complexity-based suggestions
        if graph_metrics["complexity_score"] > 8.0:
            suggestions.append({
                "type": "workflow",
                "reason": "Consider breaking complex logic into sub-workflow",
                "priority": "low",
                "suggested_config": {
                    "type": "workflow",
                    "chain_reference": "sub_workflow_template"
                }
            })
            
        # Add optimization suggestions based on graph analysis
        optimization_suggestions = self.get_optimization_suggestions()
        for opt in optimization_suggestions:
            if after_node_id in opt.get("affected_nodes", []):
                suggestions.append({
                    "type": "optimization",
                    "reason": opt["description"],
                    "priority": opt["priority"],
                    "optimization_type": opt["type"]
                })
                
        return suggestions
        
    def get_execution_state(self) -> Optional[Dict[str, Any]]:
        """Get current execution state for debugging/monitoring."""
        if not self._execution_state:
            return None
        return self._execution_state.get_execution_summary()
        
    def get_visual_layout_hints(self) -> Dict[str, Dict[str, Any]]:
        """Provide layout hints for canvas visualization.
        
        Returns positioning and grouping suggestions for nodes.
        """
        # Use enhanced graph analyzer instead of simple layout
        return self._graph_analyzer.get_spatial_layout_hints()
        
    def get_graph_metrics(self) -> Dict[str, Any]:
        """Get comprehensive graph analysis metrics."""
        metrics = self._graph_analyzer.get_metrics()
        return {
            "total_nodes": metrics.total_nodes,
            "total_edges": metrics.total_edges,
            "max_depth": metrics.max_depth,
            "parallel_opportunities": metrics.parallel_opportunities,
            "critical_path_length": metrics.critical_path_length,
            "complexity_score": metrics.complexity_score,
            "bottleneck_nodes": metrics.bottleneck_nodes,
            "leaf_nodes": metrics.leaf_nodes,
            "root_nodes": metrics.root_nodes
        }
        
    def analyze_node_impact(self, node_id: str) -> Dict[str, Any]:
        """Analyze the impact of changes to a specific node."""
        impact = self._graph_analyzer.analyze_dependency_impact(node_id)
        return {
            "node_id": impact.node_id,
            "direct_dependents": impact.direct_dependents,
            "transitive_dependents": impact.transitive_dependents,
            "affected_levels": impact.affected_levels,
            "estimated_impact_score": impact.estimated_impact_score
        }
        
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Get AI-powered optimization suggestions based on graph analysis."""
        return self._graph_analyzer.suggest_optimizations()
        
    def get_execution_path_analysis(self) -> Dict[str, Any]:
        """Get detailed analysis of possible execution paths."""
        return self._graph_analyzer.get_execution_path_analysis()
        
    def find_workflow_patterns(self, pattern_nodes: List[str]) -> List[List[str]]:
        """Find similar patterns in the workflow for refactoring opportunities."""
        return self._graph_analyzer.find_similar_patterns(pattern_nodes)
        
    def _get_node_visual_style(self, node: NodeConfig) -> Dict[str, Any]:
        """Get visual styling for a node based on its type."""
        styles = {
            "llm": {
                "shape": "rounded-rectangle",
                "color": "#4A90E2",
                "icon": "brain",
                "size": "medium"
            },
            "tool": {
                "shape": "rectangle", 
                "color": "#7ED321",
                "icon": "wrench",
                "size": "small"
            },
            "agent": {
                "shape": "hexagon",
                "color": "#BD10E0", 
                "icon": "robot",
                "size": "large"
            },
            "condition": {
                "shape": "diamond",
                "color": "#F5A623",
                "icon": "branch",
                "size": "small"
            },
            "workflow": {
                "shape": "double-rounded-rectangle",
                "color": "#50E3C2",
                "icon": "folder",
                "size": "large"
            }
        }
        
        return styles.get(node.type, {
            "shape": "rectangle",
            "color": "#9B9B9B",
            "icon": "cube",
            "size": "medium"
        })
        
    def _get_node_execution_stats(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get execution statistics for a node if available."""
        if not self._execution_state:
            return None
            
        result = self._lookup_node_result(node_id)
        if not result:
            return None
            
        stats = {
            "executed": node_id in self._execution_state.completed_nodes,
            "success": result.success,
            "duration": result.execution_time,
            "cached": getattr(result, 'cache_hit', False)
        }
        
        if result.usage:
            stats["tokens"] = result.usage.total_tokens
            
        return stats

    async def execute_node(
        self, node_id: str, input_data: Dict[str, Any]
    ) -> NodeExecutionResult:
        """Execute a single processor with enhanced NetworkX analytics tracking."""
        
        # 🚀 Enhanced NetworkX tracking - Record start time for performance analysis
        import time
        execution_start = time.time()
        self._execution_start_times[node_id] = execution_start
        
        # Track state if available
        if self._execution_state:
            self._execution_state.record_node_start(node_id)
            
        # Emit node started event with enhanced graph metadata
        node = self.nodes.get(node_id)
        if node:
            # Get rich node metadata from enhanced graph
            node_data = self.graph.graph.nodes.get(node_id, {})
            
            await self._event_handler.emit(NodeStarted(
                workflow_id=self.chain_id,
                node_id=node_id,
                node_type=node.type,
                node_name=getattr(node, 'name', None),
                level=self.graph.get_node_level(node_id),
                dependencies=node.dependencies,
                # Enhanced metadata from NetworkX graph
                metadata={
                    "complexity_score": node_data.get("complexity_score", 1.0),
                    "estimated_cost": node_data.get("estimated_cost", 0.0),
                    "parallel_safe": node_data.get("parallel_safe", True),
                    "canvas_cluster": node_data.get("canvas_cluster", "default"),
                    "is_bottleneck": node_data.get("is_bottleneck", False),
                    "is_critical_path": node_data.get("is_critical_path", False),
                }
            ))

        result = await self._executor.execute_node(node_id, input_data)
        
        # 🚀 Enhanced NetworkX tracking - Update execution statistics
        execution_time = time.time() - execution_start
        self.graph.update_execution_stats(
            node_id=node_id,
            execution_time=execution_time,
            success=result.success,
            error=str(result.error) if hasattr(result, 'error') and result.error else None
        )
        
        # 🚀 Track data transfer statistics for dependencies
        if result.success and input_data:
            estimated_data_size = len(str(input_data).encode('utf-8'))  # Rough estimate
            for dep_id in node.dependencies if node else []:
                self.graph.update_data_transfer_stats(
                    source_id=dep_id,
                    target_id=node_id,
                    transfer_time=0.001,  # Negligible for in-memory transfers
                    data_size=estimated_data_size
                )
        
        # Track completion
        if self._execution_state:
            self._execution_state.record_node_complete(node_id, result)
            
        # Emit appropriate event with enhanced metadata
        if result.success:
            await self._event_handler.emit(NodeCompleted(
                workflow_id=self.chain_id,
                node_id=node_id,
                duration_seconds=result.execution_time or 0,
                tokens_used=result.usage.total_tokens if result.usage else None,
                cost=None,  # Cost calculation from usage not yet implemented
                cache_hit=getattr(result, 'cache_hit', False)
            ))
        else:
            await self._event_handler.emit(NodeFailed(
                workflow_id=self.chain_id,
                node_id=node_id,
                error_type=type(result.error).__name__ if result.error else "Unknown",
                error_message=str(result.error) if result.error else "Unknown error"
            ))

        # 🚀 Enhanced NetworkX insights - Emit optimization insights
        if self._optimization_insights_enabled and self._emit_event:
            optimization_insights = self.graph.get_optimization_insights()
            canvas_hints = self.graph.get_canvas_layout_hints()
            
            self._emit_event("graph_insights", {
                "node_id": node_id,
                "execution_time": execution_time,
                "optimization_insights": optimization_insights,
                "bottlenecks": optimization_insights.get("bottlenecks", []),
                "critical_path": optimization_insights.get("critical_path", []),
                "parallel_opportunities": optimization_insights.get("parallel_opportunities", 0),
                "canvas_hints": canvas_hints.get(node_id, {}),
                "graph_metrics": {
                    "total_nodes": self.graph.graph.number_of_nodes(),
                    "total_edges": self.graph.graph.number_of_edges(),
                    "completion_percentage": len([
                        n for n in self.graph.graph.nodes() 
                        if self.graph.graph.nodes[n].get("execution_state") == "completed"
                    ]) / max(self.graph.graph.number_of_nodes(), 1) * 100
                }
            })

        # Handle SubDAG results
        if hasattr(result, "output") and result.output is not None:
            from ice_core.models.workflow import SubDAGResult

            if isinstance(result.output, SubDAGResult):
                subdag = await Workflow.from_dict(result.output.workflow_data)
                subdag.validate()  # From Rule 13
                return await self.execute_workflow(subdag)

        return result

    async def execute_workflow(self, workflow: "Workflow") -> NodeExecutionResult:
        """Execute nested workflow and merge results"""
        with tracer.start_as_current_span("subdag.execute") as span:
            span.set_attribute("subdag.node_count", len(workflow.nodes))
            start_time = datetime.utcnow()

            try:
                result = await workflow.execute()
                duration = (datetime.utcnow() - start_time).total_seconds()

                self.metrics.update_subdag_time(duration)
                from ice_orchestrator.execution.metrics import SubDAGMetrics

                SubDAGMetrics.record(duration)

                return result
            except Exception as e:
                span.record_exception(e)
                raise

    # ---------------------------------------------------------------------
    # Internal helpers -----------------------------------------------------
    # ---------------------------------------------------------------------

            # LLM nodes use direct API calls instead of agent pattern
    # Users must explicitly use AgentNodeConfig for LLM+tools use cases

    @staticmethod
    def _is_output_valid(node: NodeConfig, output: Any) -> bool:
        """Delegate to :class:`SchemaValidator`."""

        return SchemaValidator().is_output_valid(node, output)

    # ---------------------------------------------------------------------
    # Branch gating helpers -------------------------------------------------
    # ---------------------------------------------------------------------

    def _is_node_active(self, node_id: str) -> bool:
        """Delegate to :class:`BranchGatingResolver`."""

        return self._branch_resolver.is_node_active(node_id)

    # -----------------------------------------------------------------
    # Validation utilities --------------------------------------------
    # -----------------------------------------------------------------

    def validate_chain(self) -> list[str]:
        """Delegate to :class:`ChainValidator`."""

        return self._validator.validate_chain()

    # ------------------------------------------------------------------
    # Factory helpers ---------------------------------------------------
    # ------------------------------------------------------------------

    @classmethod
    async def from_dict(
        cls,
        payload: Dict[str, Any],
        *,
        target_version: str = "1.0.0",
        **kwargs: Any,
    ) -> "Workflow":
        """Create Workflow from dictionary.
        
        Use WorkflowBuilder for new code instead of this method.
        """
        nodes = payload.get("nodes", [])
        name = payload.get("name", "unnamed")
        
        # Convert node dicts to proper configs
        from ice_core.utils.node_conversion import convert_node_specs
        node_configs = convert_node_specs(nodes)
        
        return cls(
            nodes=node_configs,
            name=name,
            version=payload.get("version", target_version),
            **kwargs
        )

    # -------------------------------------------------------------------
    # Composition helper -------------------------------------------------
    # -------------------------------------------------------------------

    def as_workflow_node(
        self,
        id: str | None = None,
        *,
        name: str | None = None,
        workflow_ref: str | None = None,
        config_overrides: Dict[str, Any] | None = None,
        exposed_outputs: Dict[str, str] | None = None,
    ) -> "WorkflowNodeConfig":
        """Return a :class:`WorkflowNodeConfig` wrapping *self* so it can be
        embedded inside another *Workflow*.

        Example
        -------
        >>> sub_workflow = build_checkout_workflow()
        >>> # Register the workflow first
        >>> registry.register_instance(NodeType.WORKFLOW, "checkout_workflow", sub_workflow)
        >>> # Then use it as a node
        >>> parent_node = sub_workflow.as_workflow_node(
        ...     id="checkout",
        ...     workflow_ref="checkout_workflow"
        ... )
        """

        # Local import to avoid circular dependency at module import time
        from ice_core.models.node_models import WorkflowNodeConfig  # type: ignore

        return WorkflowNodeConfig(
            id=id or self.chain_id,
            name=name or self.name,
            workflow_ref=workflow_ref or self.chain_id,
            config_overrides=config_overrides or {},
            exposed_outputs=exposed_outputs or {},
            dependencies=[],
            input_selection=None,
            output_selection=None,
            type="workflow",  # explicit for clarity
        )

    def add_node(self, config: NodeConfig, depends_on: list[str] | None = None) -> str:
        """Add a new node to the workflow at runtime."""
        new_id = f"node_{len(self.nodes)}"
        config.id = new_id
        config.dependencies = depends_on or []
        # ``self.nodes`` is a mapping, not a list
        self.nodes[new_id] = config  # type: ignore[index]
        # Update the dependency graph – append to underlying NetworkX graph
        if hasattr(self.graph, "graph"):
            # Safe-guard: DependencyGraph.graph is a networkx.DiGraph
            self.graph.graph.add_node(new_id)  # type: ignore[attr-defined]
        return new_id

    def validate(self) -> None:
        """Implements WorkflowProto.validate()"""
        # ``DependencyGraph.validate_schema_alignment`` expects an *iterable* of
        # ``NodeConfig`` objects.  ``self.nodes`` is a *dict* keyed by node_id,
        # so passing it directly yields an iterator over the **keys** (str),
        # triggering AttributeError: 'str' object has no attribute 'id'.
        # We need the *values*.

        self.graph.validate_schema_alignment(list(self.nodes.values()))
        SafetyValidator.validate_node_tool_access(list(self.nodes.values()))
        ChainValidator(self.failure_policy, self.levels, self.nodes).validate_chain()

    def to_dict(self) -> Dict[str, Any]:
        """Implements WorkflowProto.to_dict()"""
        return {
            "nodes": [n.dict() for n in self.nodes.values()],
            "name": self.name,
            "version": self.version,
            "chain_id": self.chain_id,
            "max_parallel": self.max_parallel,
            "failure_policy": (
                self.failure_policy.value
                if hasattr(self.failure_policy, "value")
                else str(self.failure_policy)
            ),
        }


 