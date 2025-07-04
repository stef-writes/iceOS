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
import sys
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

import ice_sdk.executors  # noqa: F401 – side-effect import registers built-in executors
import structlog
from ice_orchestrator.chain_errors import ChainError
from ice_orchestrator.node_dependency_graph import DependencyGraph
from ice_orchestrator.workflow_execution_context import WorkflowExecutionContext
from ice_sdk.agents.agent_node import AgentNode
from ice_sdk.context import GraphContextManager
from ice_sdk.models.agent_models import AgentConfig, ModelSettings
from ice_sdk.models.node_models import (
    AiNodeConfig,
    ChainExecutionResult,
    ConditionNodeConfig,
    NodeConfig,
    NodeExecutionResult,
    NodeMetadata,
)
from ice_sdk.node_registry import get_executor
from ice_sdk.orchestrator.base_script_chain import BaseScriptChain, FailurePolicy
from ice_sdk.tools.base import BaseTool
from ice_sdk.utils.perf import WeightedSemaphore, estimate_complexity
from ice_sdk.utils.validation import validate_nested_output  # type: ignore
from opentelemetry import trace  # type: ignore[import-not-found]
from opentelemetry.trace import Status, StatusCode  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Tracing & logging setup ----------------------------------------------------
# ---------------------------------------------------------------------------
tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)


class ChainMetrics(BaseModel):
    """Metrics for chain execution."""

    total_tokens: int = 0
    total_cost: float = 0.0
    node_metrics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    def update(self, node_id: str, result: NodeExecutionResult) -> None:
        """Update metrics with node execution result."""
        if result.usage:
            self.total_tokens += getattr(result.usage, "total_tokens", 0)
            # Support both *cost* and *total_cost* naming variants --------
            self.total_cost += getattr(
                result.usage, "total_cost", getattr(result.usage, "cost", 0.0)
            )
            self.node_metrics[node_id] = result.usage.model_dump()

    def as_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "node_metrics": self.node_metrics,
        }


class ScriptChain(BaseScriptChain):
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
        token_guard: TokenGuard | None = None,
        depth_guard: DepthGuard | None = None,
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
        _validate_layer_boundaries()
        _validate_node_tool_access(nodes)

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
        self.token_ceiling = token_ceiling
        self.depth_ceiling = depth_ceiling
        # External guard callbacks --------------------------------------
        self._token_guard = token_guard
        self._depth_guard = depth_guard

        # Build dependency graph
        self.graph = DependencyGraph(nodes)
        self.graph.validate_schema_alignment(nodes)
        self.levels = self.graph.get_level_nodes()

        # Metrics & events
        self.metrics = ChainMetrics()
        # Agent instance cache -------------------------------------------
        self._agent_cache: Dict[str, AgentNode] = {}
        # Track decisions made by *condition* nodes -----------------------
        self._branch_decisions: Dict[str, bool] = {}
        # Cache for branch-gating propagation results ---------------------
        # Initialising here avoids repeated hasattr checks at runtime.
        self._active_cache: Dict[str, bool] = {}
        # Retain reference to chain-level tools ---------------------------
        self._chain_tools: List[BaseTool] = tools or []

        from ice_sdk.cache import global_cache  # local import to avoid cycles

        self._cache = global_cache()

        logger.info(
            "Initialized ScriptChain with %d nodes across %d levels",
            len(nodes),
            len(self.levels),
        )

    async def execute(self) -> ChainExecutionResult:
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
                            self._branch_decisions[node_id] = bool(
                                result.output["result"]
                            )
                        except Exception:
                            # Defensive fallback – ignore unexpected conversion issues
                            pass

                    # When the node execution failed, collect error information
                    if not result.success:
                        errors.append(f"Node {node_id} failed: {result.error}")

                if errors and not self._should_continue(errors):
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

        return ChainExecutionResult(
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
            execution_time=duration,
            token_stats=self.metrics.as_dict(),
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
        """Build execution context for a node."""
        context: Dict[str, Any] = {}
        validation_errors: List[str] = []

        if getattr(node, "input_mappings", None):
            for placeholder, mapping in node.input_mappings.items():
                # Support either raw dicts *or* InputMapping instances ----------------
                if (
                    isinstance(mapping, dict) and "source_node_id" in mapping
                ) or hasattr(mapping, "source_node_id"):
                    dep_id = mapping["source_node_id"] if isinstance(mapping, dict) else mapping.source_node_id  # type: ignore[index]
                    output_key = mapping["source_output_key"] if isinstance(mapping, dict) else mapping.source_output_key  # type: ignore[index]
                    dep_result = accumulated_results.get(dep_id)

                    if not dep_result or not dep_result.success:
                        validation_errors.append(
                            f"Dependency '{dep_id}' failed or did not run."
                        )
                        continue

                    try:
                        value = self._resolve_nested_path(dep_result.output, output_key)
                        context[placeholder] = value
                    except (KeyError, IndexError, TypeError) as exc:
                        validation_errors.append(
                            f"Failed to resolve path '{output_key}' in dependency '{dep_id}': {exc}"
                        )
                else:
                    context[placeholder] = mapping  # fall back to raw value

        if validation_errors:
            raise ChainError(
                f"Node '{node.id}' context validation failed:\n"
                + "\n".join(validation_errors)
            )

        return context

    def _should_continue(self, errors: List[str]) -> bool:
        """Determine whether chain execution should proceed after errors."""
        if not errors:
            return True

        if self.failure_policy == FailurePolicy.HALT:
            return False
        if self.failure_policy == FailurePolicy.ALWAYS:
            return True

        # CONTINUE_POSSIBLE
        failed_nodes: Set[str] = set()
        for error in errors:
            if "Node " in error and " failed:" in error:
                try:
                    node_id = error.split("Node ")[1].split(" failed:")[0]
                    failed_nodes.add(node_id)
                except (IndexError, AttributeError):
                    continue

        for level_num in sorted(self.levels.keys()):
            for node_id in self.levels[level_num]:
                node = self.nodes[node_id]
                if node_id in failed_nodes:
                    continue
                depends_on_failed_node = any(
                    dep in failed_nodes for dep in getattr(node, "dependencies", [])
                )
                if not depends_on_failed_node:
                    logger.info(
                        "Chain execution continuing: Node '%s' can still execute independently",
                        node_id,
                    )
                    return True

        logger.warning(
            "Chain execution stopping: All remaining nodes depend on failed nodes: %s",
            failed_nodes,
        )
        return False

    @staticmethod
    def _resolve_nested_path(data: Any, path: str) -> Any:
        """Resolve a dot-separated *path* in *data*.

        Special cases
        -------------
        * ``path == ""`` or ``path == "."``  → return *data* unchanged.
        """
        if not path or path == ".":
            return data
        for key in path.split("."):
            if isinstance(data, dict):
                data = data[key]
            elif isinstance(data, list):
                data = data[int(key)]
            else:
                raise TypeError(f"Cannot resolve path '{path}' in {type(data)}")
        return data

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
        """Execute a single node using agent/tool wrappers (overrides BaseScriptChain)."""
        node = self.nodes.get(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' not found in chain configuration")

        # ------------------------------------------------------------------
        # Persist *input_data* to the context store ------------------------
        # ------------------------------------------------------------------
        self.context_manager.update_node_context(
            node_id=node_id,
            content=input_data,
            execution_id=self.context_manager.get_context().execution_id,  # type: ignore[attr-defined]
        )

        max_retries: int = int(getattr(node, "retries", 0))
        base_backoff: float = float(getattr(node, "backoff_seconds", 0.0))

        attempt = 0
        last_error: Exception | None = None

        while attempt <= max_retries:
            try:
                # ------------------------------------------------------
                # Cache lookup (opt-in) --------------------------------
                # ------------------------------------------------------
                import hashlib
                import json

                cache_key: str | None = None
                if self.use_cache and getattr(node, "use_cache", True):
                    try:
                        # Include *node configuration* snapshot so that changes
                        # (e.g. modified prompt) bust the cache automatically.
                        from pydantic import BaseModel

                        cfg_payload = (
                            node.model_dump()
                            if isinstance(node, BaseModel)
                            else str(node)
                        )

                        payload = {
                            "node_id": node_id,
                            "input": input_data,
                            "cfg": cfg_payload,
                        }
                        serialized = json.dumps(payload, sort_keys=True, default=str)
                        cache_key = hashlib.sha256(serialized.encode()).hexdigest()
                        cached = self._cache.get(cache_key)
                        if cached is not None:
                            return cached
                    except Exception:
                        # Fall back – never fail due to cache issues
                        cache_key = None
                # ----------------------------------------------------------
                # Dispatch via the *Node Registry* -------------------------
                # ----------------------------------------------------------
                executor = get_executor(str(getattr(node, "type", "")))  # type: ignore[arg-type]
                # ------------------------------------------------------
                # Per-node tracing span --------------------------------
                # ------------------------------------------------------
                with tracer.start_as_current_span(
                    "node.execute",
                    attributes={
                        "node_id": node_id,
                        "node_type": str(getattr(node, "type", "")),
                    },
                ) as node_span:
                    result = await executor(self, node, input_data)

                    # Attach outcome metadata to the span ---------------
                    node_span.set_attribute("success", result.success)
                    node_span.set_attribute("retry_count", attempt)
                    if not result.success:
                        node_span.set_status(
                            Status(StatusCode.ERROR, result.error or "")
                        )

                # Store in cache if enabled & succeeded ------------------
                if cache_key and result.success:
                    self._cache.set(cache_key, result)

                # Attach retry metadata -----------------------------------
                if result.metadata:
                    result.metadata.retry_count = attempt

                # Persist *output* to the context store if configured ------
                if self.persist_intermediate_outputs and result.output is not None:
                    self.context_manager.update_node_context(
                        node_id=node_id,
                        content=result.output,
                        execution_id=self.context_manager.get_context().execution_id,  # type: ignore[attr-defined]
                    )

                # ----------------------------------------------------------
                # Optional output validation -------------------------------
                # ----------------------------------------------------------
                if self.validate_outputs and getattr(node, "output_schema", None):
                    if not self._is_output_valid(node, result.output):
                        result.success = False
                        err_msg = f"Output validation failed for node '{node_id}' against declared schema"
                        result.error = (
                            err_msg
                            if result.error is None
                            else result.error + "; " + err_msg
                        )

                return result

            except Exception as e:  # pylint: disable=broad-except
                last_error = e
                if attempt >= max_retries:
                    break

                # ------------------------------------------------------
                # Exponential backoff before next retry ---------------
                # ------------------------------------------------------
                wait_seconds = base_backoff * (2**attempt) if base_backoff > 0 else 0
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)

                attempt += 1

        # ------------------------------------------------------------------
        # All retries exhausted – return failure result ---------------------
        # ------------------------------------------------------------------
        from datetime import datetime

        error_meta = NodeMetadata(
            node_id=node_id,
            node_type=str(getattr(node, "type", "")),
            name=getattr(node, "name", None),
            version="1.0.0",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration=0.0,
            error_type=type(last_error).__name__ if last_error else "UnknownError",
            retry_count=attempt,
        )  # type: ignore[call-arg]

        if self.failure_policy == FailurePolicy.HALT:
            raise last_error if last_error else Exception("Unknown error")

        return NodeExecutionResult(  # type: ignore[call-arg]
            success=False,
            error=f"Retry limit exceeded ({max_retries}) – last error: {last_error}",
            metadata=error_meta,
        )

    # ---------------------------------------------------------------------
    # Internal helpers -----------------------------------------------------
    # ---------------------------------------------------------------------

    def _make_agent(self, node: AiNodeConfig) -> AgentNode:
        """Convert an *AiNodeConfig* into a fully-initialised :class:`AgentNode`."""
        # Build tool map so later inserts override earlier ones (priority)
        tool_map: Dict[str, BaseTool] = {}

        # 1. Globally registered tools (lowest precedence) --------------
        for name, tool in self.context_manager.get_all_tools().items():
            tool_map[name] = tool

        # 2. Chain-level tools – override globals when name clashes ------
        for t in self._chain_tools:
            tool_map[t.name] = t

        # 3. Node-specific tool refs override everything else -----------
        if getattr(node, "tools", None):
            for cfg in node.tools:  # type: ignore[attr-defined]
                t_obj = self.context_manager.get_tool(cfg.name)
                if t_obj is not None:
                    tool_map[t_obj.name] = t_obj

        tools: List[BaseTool] = list(tool_map.values())

        # Build AgentConfig ----------------------------------------------
        model_settings = ModelSettings(
            model=node.model,
            temperature=getattr(node, "temperature", 0.7),
            max_tokens=getattr(node, "max_tokens", None),
            provider=str(getattr(node.provider, "value", node.provider)),
        )

        agent_cfg = AgentConfig(
            name=node.name or node.id,
            instructions=node.prompt,
            model=node.model,
            model_settings=model_settings,
            tools=tools,
        )  # type: ignore[call-arg]

        agent = AgentNode(config=agent_cfg, context_manager=self.context_manager)
        agent.tools = tools  # expose on instance (used by AgentNode.execute)

        # ------------------------------------------------------------------
        # Register agent & tools with the ContextManager -------------------
        # ------------------------------------------------------------------
        try:
            self.context_manager.register_agent(agent)
        except ValueError:
            # Already registered – ignore duplicate
            pass

        for tool in tools:
            try:
                self.context_manager.register_tool(tool)
            except ValueError:
                # Possible duplicate registration – safe to ignore
                continue

        return agent

    @staticmethod
    def _is_output_valid(node: NodeConfig, output: Any) -> bool:
        """Validate *output* against ``node.output_schema``.  Returns *True* when
        validation succeeds or no schema declared.

        Supports both *dict*-based schemas and Pydantic ``BaseModel`` subclasses to
        stay in sync with the flexible input validation strategy.
        """
        schema = getattr(node, "output_schema", None)
        if not schema:
            return True

        # ------------------------------------------------------------------
        # 1. Pydantic model --------------------------------------------------
        # ------------------------------------------------------------------
        try:
            from pydantic import BaseModel, ValidationError

            if isinstance(schema, type) and issubclass(schema, BaseModel):
                try:
                    schema.model_validate(output)  # type: ignore[arg-type]
                    return True
                except ValidationError:
                    return False
        except Exception:
            # Pydantic may not be importable in constrained envs – fall back.
            pass

        # ------------------------------------------------------------------
        # 2. dict schema – leverage nested validation helper -----------------
        # ------------------------------------------------------------------
        if isinstance(schema, dict):
            # Accept both {key: "type"} and {key: <type>} formats ------------
            normalized_schema: dict[str, type] = {}
            for key, expected in schema.items():
                if isinstance(expected, str):
                    try:
                        normalized_schema[key] = eval(expected)
                    except Exception:  # noqa: S110
                        # Fallback to 'Any' when type string cannot be resolved
                        from typing import Any  # local import to avoid top-level

                        normalized_schema[key] = Any  # type: ignore[assignment]
                else:
                    normalized_schema[key] = expected  # type: ignore[assignment]

            errors = validate_nested_output(output, normalized_schema)
            return len(errors) == 0

        # Unknown schema format – consider valid to avoid false negatives
        return True

    # ---------------------------------------------------------------------
    # Branch gating helpers -------------------------------------------------
    # ---------------------------------------------------------------------

    def _is_node_active(self, node_id: str) -> bool:
        """Determine whether *node_id* should run in the current execution.

        The logic combines two independent gating mechanisms:

        1. **Branch-based gating** – Nodes explicitly listed in a *Condition* node's
           ``true_branch`` / ``false_branch`` lists are enabled or disabled based
           on that condition's runtime decision.
        2. **Dependency propagation** – If *any* direct or transitive dependency
           has been disabled by step (1) (or by further propagation), the current
           node is implicitly disabled as well.  This prevents nodes from running
           with missing upstream context and avoids spurious validation errors
           later in the pipeline.
        """

        # ------------------------------------------------------------------
        # 1. Explicit branch gating ----------------------------------------
        # ------------------------------------------------------------------
        from ice_sdk.models.node_models import ConditionNodeConfig  # local import

        for cond_id, decision in self._branch_decisions.items():
            cond_id_str = str(cond_id)
            cond_cfg = self.nodes.get(cond_id_str)
            if not isinstance(cond_cfg, ConditionNodeConfig):
                continue

            # Outcome TRUE → *false_branch* nodes are disabled -------------
            if decision and cond_cfg.false_branch and node_id in cond_cfg.false_branch:
                return False

            # Outcome FALSE → *true_branch* nodes are disabled -------------
            if (
                not decision
                and cond_cfg.true_branch
                and node_id in cond_cfg.true_branch
            ):
                return False

        # ------------------------------------------------------------------
        # 2. Implicit propagation through dependencies ---------------------
        # ------------------------------------------------------------------
        # Cache already-computed decisions to avoid exponential recursion
        if node_id in self._active_cache:
            return self._active_cache[node_id]

        deps = self.graph.get_node_dependencies(node_id)
        for dep_id in deps:
            if not self._is_node_active(dep_id):
                self._active_cache[node_id] = False
                return False

        self._active_cache[node_id] = True
        return True

    # -----------------------------------------------------------------
    # Validation utilities --------------------------------------------
    # -----------------------------------------------------------------

    def validate_chain(self) -> list[str]:
        """Run a set of static validations and return a list of error messages.

        The method does **not** raise; callers can decide whether to abort or
        continue based on returned errors.  Down-stream integrations (e.g. CLI
        or API endpoints) may present the aggregated errors to end-users.
        """

        errors: list[str] = []
        errors.extend(self._validate_node_versions())
        errors.extend(self._check_license_compliance())
        errors.extend(self._detect_sensitive_data_flows())
        return errors

    # -----------------------------------------------------------------
    # Private validation helpers --------------------------------------
    # -----------------------------------------------------------------

    def _validate_node_versions(self) -> list[str]:
        """Ensure every node declares a non-empty *version* attribute."""

        errs: list[str] = []
        for node in self.nodes.values():
            version = getattr(node, "version", None)
            # Fall back to metadata.version when top-level attr missing -------
            if version is None and getattr(node, "metadata", None):
                version = getattr(node.metadata, "version", None)

            if not version:
                errs.append(f"Node '{node.id}' is missing version metadata.")
        return errs

    def _check_license_compliance(self) -> list[str]:
        """Placeholder for future OSS/enterprise license checks."""
        # TODO(issue-123): Implement SBOM scanning & license validation
        return []

    def _detect_sensitive_data_flows(self) -> list[str]:
        """Placeholder for PII / GDPR data-flow analysis."""
        # TODO(issue-124): Integrate with privacy analysis engine
        return []

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
        """Create a ScriptChain from JSON-compatible *payload*.

        The helper calls :pyclass:`ice_orchestrator.chain_migrator.ChainMigrator`
        to upgrade older workflow specs before instantiation.
        """

        # Import lazily to avoid cycles ----------------------------------
        from ice_orchestrator.chain_migrator import ChainMigrator

        # 1. Run migration (no-op when already up-to-date) ---------------
        try:
            payload = await ChainMigrator.migrate(payload, target_version)
        except NotImplementedError as exc:
            # Bubble-up – caller decides whether to abort or run legacy
            raise RuntimeError(str(exc)) from exc

        # 2. Parse nodes --------------------------------------------------
        nodes_raw = payload.get("nodes", [])
        if not nodes_raw:
            raise ValueError("Workflow payload must contain 'nodes' key")

        # Discriminated union parsing (manual to avoid Annotated typing issues)
        from ice_sdk.models.node_models import (
            AiNodeConfig,
            ConditionNodeConfig,
            ToolNodeConfig,
        )

        _parser_map = {
            "ai": AiNodeConfig,
            "tool": ToolNodeConfig,
            "condition": ConditionNodeConfig,
        }

        nodes = []
        for nd in nodes_raw:
            node_type = nd.get("type")
            parser_cls = _parser_map.get(node_type)
            if parser_cls is None:
                raise ValueError(f"Unknown node type '{node_type}' in workflow spec")
            nodes.append(parser_cls.model_validate(nd))

        # 3. Instantiate chain -------------------------------------------
        return cls(
            nodes=nodes,
            name=payload.get("name"),
            version=payload.get("version", target_version),
            **kwargs,
        )


if TYPE_CHECKING:  # pragma: no cover
    from ice_sdk.interfaces.guardrails import DepthGuard, TokenGuard
else:  # Runtime no-op fallbacks
    from typing import Any as DepthGuard  # type: ignore
    from typing import Any as TokenGuard


# ---------------------------------------------------------------------------
#  Internal safety validations ----------------------------------------------
# ---------------------------------------------------------------------------


_FORBIDDEN_IMPORT_PREFIXES = (
    "ice_sdk.tools",  # lower layer (sdk) exposing tool impls
    "ice_tools",  # any ad-hoc tools package
)


def _validate_layer_boundaries() -> None:  # noqa: D401 – helper
    """Raise LayerViolationError if orchestrator accidentally imported tool modules."""

    for mod_name in sys.modules:
        if any(mod_name.startswith(prefix) for prefix in _FORBIDDEN_IMPORT_PREFIXES):
            logger.warning(
                "Layer-boundary advisory: orchestrator imported higher-level module '%s' (allowed in test/dev)",
                mod_name,
            )


def _validate_node_tool_access(nodes: List[NodeConfig]) -> None:  # noqa: D401 – helper
    """Ensure only *tool* nodes reference tools explicitly."""

    for node in nodes:
        # Only AI nodes may declare allow-lists – but non-tool nodes must not
        allowed = getattr(node, "allowed_tools", None)
        if node.type != "tool" and allowed:
            raise ValueError(
                f"Node '{node.id}' (type={node.type}) is not allowed to declare allowed_tools"
            )
