"""Core script chain implementation for workflow orchestration.

This module provides a simplified but powerful implementation of workflow orchestration
that integrates with the new agent system while preserving all key functionality:
- Level-based parallel execution
- Robust error handling
- Context & state management
- Performance features
- Observability
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import structlog
from opentelemetry import trace  # type: ignore[import-not-found]
from opentelemetry.trace import Status, StatusCode  # type: ignore[import-not-found]

import ice_sdk.executors  # noqa: F401 – side-effect import registers built-in executors
from ice_core.utils.perf import WeightedSemaphore, estimate_complexity
from ice_orchestrator.core import ChainFactory
from ice_orchestrator.execution.agent_factory import AgentFactory
from ice_orchestrator.execution.executor import NodeExecutor
from ice_orchestrator.execution.metrics import ChainMetrics
from ice_orchestrator.graph.dependency_graph import DependencyGraph
from ice_orchestrator.graph.level_resolver import BranchGatingResolver
from ice_orchestrator.utils.context_builder import ContextBuilder
from ice_orchestrator.validation import ChainValidator, SafetyValidator, SchemaValidator
from ice_sdk.agents.agent_node import AgentNode
from ice_sdk.config import runtime_config
from ice_sdk.context import GraphContextManager
from ice_sdk.models.node_models import (
    AiNodeConfig,
    ChainExecutionResult,
    ConditionNodeConfig,
    NestedChainConfig,
    NodeConfig,
    NodeExecutionResult,
    NodeMetadata,
)
from ice_sdk.orchestrator.base_script_chain import BaseScriptChain, FailurePolicy
from ice_sdk.orchestrator.workflow_execution_context import WorkflowExecutionContext
from ice_sdk.tools.base import BaseTool

# ---------------------------------------------------------------------------
# Tracing & logging setup ----------------------------------------------------
# ---------------------------------------------------------------------------
tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)


class ScriptChain(BaseScriptChain):  # type: ignore[misc]  # mypy cannot resolve BaseScriptChain across namespace package boundary
    """Execute a directed acyclic workflow using level-based parallelism.

    Nodes at the same topological level (i.e. depth in the dependency DAG)
    are executed concurrently up to the configured max_parallel limit.

    Features:
    - Level-based parallel execution
    - Robust error handling with configurable policies
    - Context & state management
    - Performance features (caching, large output handling)
    - Observability (metrics, tracing, callbacks)
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
        tools: Optional[List[BaseTool]] = None,
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
        """Initialize script chain.

        Args:
            nodes: List of node configurations
            name: Chain name
            version: Chain version
            context_manager: Context manager
            callbacks: List of callbacks
            max_parallel: Maximum parallel executions
            persist_intermediate_outputs: Whether to persist outputs
            tools: List of tools available to nodes
            initial_context: Initial execution context
            workflow_context: Workflow execution context
            chain_id: Unique chain identifier
            failure_policy: Failure handling policy
            validate_outputs: Whether to validate node outputs
            token_ceiling: Token ceiling for chain execution
            depth_ceiling: Depth ceiling for chain execution
            token_guard: Token guard for chain execution
            depth_guard: Depth guard for chain execution
            session_id: Session identifier
            use_cache: Chain-level cache toggle
        """
        self.chain_id = chain_id or f"chain_{datetime.utcnow().isoformat()}"
        # Semantic version for migration tracking -----------------------
        self.version: str = version

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

        # Validator helper ----------------------------------------------------
        self._validator = ChainValidator(self.failure_policy, self.levels, self.nodes)

        # Metrics & events
        self.metrics = ChainMetrics()
        # Executor helper -----------------------------------------------------
        self._executor = NodeExecutor(self)
        # Agent factory helper ------------------------------------------------
        self._agent_factory = AgentFactory(self.context_manager, self._chain_tools)
        # Schema validator helper ---------------------------------------------
        self._schema_validator = SchemaValidator()
        # Agent instance cache -------------------------------------------
        self._agent_cache: Dict[str, AgentNode] = {}
        # Track decisions made by *condition* nodes -----------------------
        self._branch_resolver = BranchGatingResolver(self.nodes, self.graph)
        # Preserve original attrs for B/C (alias to resolver internals)
        self._branch_decisions = self._branch_resolver.branch_decisions  # type: ignore[attr-defined]
        self._active_cache = self._branch_resolver.active_cache  # type: ignore[attr-defined]

        from ice_sdk.cache import global_cache  # local import to avoid cycles

        self._cache = global_cache()

        logger.info(
            "Initialized ScriptChain with %d nodes across %d levels",
            len(nodes),
            len(self.levels),
        )

    async def execute(self) -> NodeExecutionResult:
        """Execute the workflow and return a ChainExecutionResult."""
        start_time = datetime.utcnow()
        results: Dict[str, NodeExecutionResult] = {}
        errors: List[str] = []

        logger.info(
            "Starting execution of chain '%s' (ID: %s)", self.name, self.chain_id
        )

        with tracer.start_as_current_span(
            "chain.execute",
            attributes={
                "chain_id": self.chain_id,
                "chain_name": self.name,
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
                                    "Token ceiling exceeded (%s); aborting chain.",
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
                "Completed chain execution",
                chain=self.name,
                chain_id=self.chain_id,
                duration=duration,
            )

            chain_span.set_attribute("success", len(errors) == 0)
            if errors:
                chain_span.set_status(Status(StatusCode.ERROR, ";".join(errors)))
            chain_span.end()

        final_node_id = self.graph.get_leaf_nodes()[0]

        # Wrap ChainExecutionResult as NodeExecutionResult for ABC compliance
        chain_result = ChainExecutionResult(
            success=len(errors) == 0,
            output=results,
            error="\n".join(errors) if errors else None,
            metadata=NodeMetadata(
                node_id=final_node_id,
                node_type="script_chain",
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
        )

    async def _execute_level(
        self,
        level_nodes: List[NodeConfig],
        accumulated_results: Dict[str, NodeExecutionResult],
    ) -> Dict[str, NodeExecutionResult]:
        """Execute all nodes at a given level in parallel."""
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
        # Gather with *return_exceptions* so that a single node failure does not
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

                    from ice_sdk.models.node_models import (
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

                from ice_sdk.models.node_models import NodeExecutionResult, NodeMetadata

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
        return level_results

    def _build_node_context(
        self,
        node: NodeConfig,
        accumulated_results: Dict[str, NodeExecutionResult],
    ) -> Dict[str, Any]:
        """Compose node input context.

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
        except Exception:  # noqa: BLE001 – never break execution due to ctx issues
            pass

        return node_ctx

    @staticmethod
    def _resolve_nested_path(data: Any, path: str) -> Any:
        """Delegate to :class:`ContextBuilder`."""

        return ContextBuilder.resolve_nested_path(data, path)  # type: ignore[return-value]  # dynamic path resolution returns Any

    # ---------------------------------------------------------------------
    # Graph inspection public API -----------------------------------------
    # ---------------------------------------------------------------------

    def get_node_dependencies(self, node_id: str) -> List[str]:
        """Get dependencies for a node."""
        return self.graph.get_node_dependencies(node_id)

    def get_node_dependents(self, node_id: str) -> List[str]:
        """Get dependents for a node."""
        return self.graph.get_node_dependents(node_id)

    def get_node_level(self, node_id: str) -> int:
        """Get execution level for a node."""
        return self.graph.get_node_level(node_id)

    def get_level_nodes(self, level: int) -> List[str]:
        """Get nodes at a specific level."""
        return self.levels.get(level, [])

    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics."""
        return self.metrics.as_dict()

    async def execute_node(
        self, node_id: str, input_data: Dict[str, Any]
    ) -> NodeExecutionResult:
        """Execute a single node – now delegated to *NodeExecutor* utility."""

        return await self._executor.execute_node(node_id, input_data)

    # ---------------------------------------------------------------------
    # Internal helpers -----------------------------------------------------
    # ---------------------------------------------------------------------

    def _make_agent(self, node: AiNodeConfig) -> AgentNode:
        """Delegate to :class:`AgentFactory`."""

        return self._agent_factory.make_agent(node)

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
    ) -> "ScriptChain":
        """Delegate to :class:`ChainFactory`."""

        chain_obj = await ChainFactory.from_dict(
            payload, target_version=target_version, **kwargs
        )
        return chain_obj

    # -------------------------------------------------------------------
    # Composition helper -------------------------------------------------
    # -------------------------------------------------------------------

    def as_nested_node(  # noqa: D401 – helper name
        self,
        id: str | None = None,
        *,
        name: str | None = None,
        input_mappings: Dict[str, Any] | None = None,
        exposed_outputs: Dict[str, str] | None = None,
    ) -> "NestedChainConfig":
        """Return a :class:`NestedChainConfig` wrapping *self* so it can be
        embedded inside another *ScriptChain*.

        Example
        -------
        >>> sub_chain = build_checkout_chain()
        >>> parent_node = sub_chain.as_nested_node(
        ...     id="checkout",
        ...     input_mappings={"amount": InputMapping(...)}
        ... )
        """

        # Local import to avoid circular dependency at module import time
        from ice_sdk.models.node_models import NestedChainConfig  # type: ignore

        return NestedChainConfig(
            id=id or self.chain_id,
            name=name or self.name,
            chain=self,
            input_mappings=input_mappings or {},
            exposed_outputs=exposed_outputs or {},
            dependencies=[],
            type="nested_chain",  # explicit for clarity
        )
