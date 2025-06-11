"""
Enhanced workflow orchestration system with level-based parallel execution and robust context management
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Structured logging & tracing ------------------------------------------------
import structlog
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.chains.events import EventDispatcher
from app.chains.metrics import ChainMetrics
from app.chains.orchestration.base_script_chain import BaseScriptChain, FailurePolicy

# Orchestration & app-specific imports ---------------------------------------
from app.chains.orchestration.node_dependency_graph import DependencyGraph
from app.chains.orchestration.workflow_execution_context import WorkflowExecutionContext
from app.models.node_models import (
    ChainExecutionResult,
    InputMapping,
    NodeConfig,
    NodeExecutionResult,
    NodeMetadata,
)
from app.nodes.factory import node_factory
from app.utils.artifact_store import ArtifactStore

# Initialize tracing & logger AFTER all imports to satisfy lint rules ---------
tracer = trace.get_tracer(__name__)

# Create a structlog logger. Configuration happens in ice_sdk.__init__
logger = structlog.get_logger(__name__)


class LevelBasedScriptChain(BaseScriptChain):
    """
    Orchestrates workflow execution using level-based parallelism and robust context management.
    Delegates graph, node execution, metrics, and event logic to dedicated modules.
    Implements level-based (topological) execution strategy.
    """

    def __init__(
        self,
        nodes: List[NodeConfig],
        name: Optional[str] = None,
        context_manager: Optional[Any] = None,
        callbacks: Optional[List[Any]] = None,
        max_parallel: int = 5,
        persist_intermediate_outputs: bool = True,
        tool_service: Optional[Any] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[WorkflowExecutionContext] = None,
        chain_id: Optional[str] = None,
        failure_policy: FailurePolicy = FailurePolicy.CONTINUE_POSSIBLE,
        artifact_store: Optional[ArtifactStore] = None,
        validate_outputs: bool = True,
    ):
        self.chain_id = chain_id or os.urandom(8).hex()
        super().__init__(
            nodes,
            name,
            context_manager,
            callbacks,
            max_parallel,
            persist_intermediate_outputs,
            tool_service,
            initial_context,
            workflow_context,
            failure_policy,
        )
        self.validate_outputs = validate_outputs
        self.graph = DependencyGraph(nodes)
        self.graph.validate_schema_alignment(nodes)
        self.levels = self.graph.get_level_nodes()
        self.metrics = ChainMetrics(self.name)
        self.events = EventDispatcher(self.callbacks)
        # Instantiate all nodes using node_factory
        self.node_instances = {
            node_id: node_factory(
                node,
                context_manager=self.context_manager,
                llm_config=getattr(node, "llm_config", None),
                callbacks=self.callbacks,
                tool_service=self.tool_service,
            )
            for node_id, node in self.nodes.items()
        }
        self.artifact_store = artifact_store
        self.large_output_threshold = 256 * 1024  # 256 KiB
        self._cache = {}
        logger.info(
            f"Initialized ScriptChain with {len(nodes)} nodes in {len(self.levels)} levels"
        )

    async def execute(self) -> ChainExecutionResult:
        start_time = datetime.utcnow()
        results = {}
        errors = []
        node_executor = NodeExecutor(
            context_manager=self.context_manager,
            chain_id=self.chain_id,
            persist_intermediate_outputs=self.persist_intermediate_outputs,
            callbacks=self.callbacks,
            tool_service=self.tool_service,
            initial_context=self.initial_context,
            workflow_context=self.workflow_context,
            artifact_store=self.artifact_store,
            large_output_threshold=self.large_output_threshold,
            cache=self._cache,
            enforce_output_schema=self.validate_outputs,
        )
        logger.info(f"Starting execution of chain '{self.name}' (ID: {self.chain_id})")

        with tracer.start_as_current_span(
            "chain.execute",
            attributes={
                "chain_id": self.chain_id,
                "chain_name": self.name,
                "node_count": len(self.nodes),
            },
        ) as chain_span:
            for level_num in sorted(self.levels.keys()):
                level_node_ids = self.levels[level_num]
                level_nodes = [
                    self.node_instances[node_id] for node_id in level_node_ids
                ]
                level_results = await self._execute_level(
                    level_nodes, node_executor, results
                )
                for node_id, result_obj in level_results.items():
                    # Always store the full NodeExecutionResult so that downstream nodes can
                    # reliably inspect attributes such as `success`, `output`, etc.
                    results[node_id] = result_obj

                    if result_obj.success:
                        # Update chain-level metrics only for successful executions
                        if hasattr(result_obj, "usage") and result_obj.usage:
                            self.metrics.update(node_id, result_obj)
                    else:
                        errors.append(f"Node {node_id} failed: {result_obj.error}")
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

        # Get the final result from the last node in the chain
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
            ),
            execution_time=duration,
            token_stats=self.metrics.as_dict(),
        )

    async def _execute_level(
        self,
        level_nodes: List[Any],
        node_executor: "NodeExecutor",
        accumulated_results: Dict[str, NodeExecutionResult],
    ) -> Dict[str, NodeExecutionResult]:
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def process_node(node):
            async with semaphore:
                return await node_executor.execute_node(node, accumulated_results)

        tasks = [process_node(node) for node in level_nodes]
        results = await asyncio.gather(*tasks)
        return dict(results)

    def _should_continue(self, errors: List[str]) -> bool:
        """Determine whether chain execution should proceed after errors based on policy."""

        # No errors → always continue
        if not errors:
            return True

        # Policy: HALT ------------------------------------------------------
        if self.failure_policy == FailurePolicy.HALT:
            return False

        # Policy: ALWAYS ----------------------------------------------------
        if self.failure_policy == FailurePolicy.ALWAYS:
            return True

        # Policy: CONTINUE_POSSIBLE (default) ------------------------------
        failed_nodes: set[str] = set()
        for error in errors:
            if "Node " in error and " failed:" in error:
                try:
                    node_id = error.split("Node ")[1].split(" failed:")[0]
                    failed_nodes.add(node_id)
                except (IndexError, AttributeError):
                    continue

        # If there exists at least one pending node that does not depend on
        # a failed node we can keep going; otherwise stop.
        for level_num in sorted(self.levels.keys()):
            for node_id in self.levels[level_num]:
                node = self.nodes[node_id]
                if node_id in failed_nodes:
                    continue
                depends_on_failed_node = any(
                    dep_id in failed_nodes
                    for dep_id in getattr(node, "dependencies", [])
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

    # Expose graph queries for external use
    def get_node_dependencies(self, node_id: str) -> List[str]:
        return self.graph.get_node_dependencies(node_id)

    def get_node_dependents(self, node_id: str) -> List[str]:
        return self.graph.get_node_dependents(node_id)

    def get_node_level(self, node_id: str) -> int:
        return self.graph.get_node_level(node_id)

    def get_level_nodes(self, level: int) -> List[str]:
        return self.levels.get(level, [])

    def get_metrics(self) -> Dict[str, Any]:
        return self.metrics.as_dict()


# ---------------------------------------------------------------------------
# Local inline copy of the former ``NodeExecutor``.  By embedding it here we
# eliminate one indirection layer and make script-chain execution easier to
# reason about.
# ---------------------------------------------------------------------------


class NodeExecutor:
    """Handles execution of a single node, including context resolution."""

    def __init__(
        self,
        context_manager: Any,
        chain_id: str,
        persist_intermediate_outputs: bool = True,
        callbacks: Optional[List[Any]] = None,
        tool_service: Optional[Any] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[WorkflowExecutionContext] = None,
        artifact_store: Optional["ArtifactStore"] = None,
        large_output_threshold: int = 256 * 1024,  # 256 KiB
        cache: Optional[dict[str, NodeExecutionResult]] = None,
        enforce_output_schema: bool = True,
    ):
        self.context_manager = context_manager
        self.chain_id = chain_id
        self.persist_intermediate_outputs = persist_intermediate_outputs
        self.callbacks = callbacks or []
        self.tool_service = tool_service
        self.initial_context = initial_context or {}
        self.workflow_context = workflow_context or WorkflowExecutionContext()
        self.artifact_store = artifact_store
        self.large_output_threshold = large_output_threshold
        self._cache = cache or {}
        self.enforce_output_schema = enforce_output_schema

    async def execute_node(
        self, node, accumulated_results: Dict[str, NodeExecutionResult]
    ) -> Tuple[str, NodeExecutionResult]:
        start_time = datetime.utcnow()
        node_id = node.id

        # OpenTelemetry span --------------------------------------------------
        with tracer.start_as_current_span(
            "node.execute",
            attributes={"node_id": node_id, "chain_id": self.chain_id},
        ) as span:
            try:
                # Build context from dependencies and input mappings -----------------
                context: Dict[str, Any] = {}
                validation_errors: List[str] = []

                if getattr(node, "input_mappings", None):
                    for placeholder, mapping in node.input_mappings.items():
                        # Two possibilities: mapping reference (InputMapping) or literal value.
                        is_reference = isinstance(mapping, InputMapping) or (
                            isinstance(mapping, dict)
                            and "source_node_id" in mapping
                            and "source_output_key" in mapping
                        )

                        if is_reference:
                            # Normalise to InputMapping instance for attribute access.
                            if isinstance(mapping, dict):
                                mapping = InputMapping(**mapping)

                            dep_id = mapping.source_node_id
                            output_key = mapping.source_output_key
                            dep_result = accumulated_results.get(dep_id)

                            if not dep_result or not dep_result.success:
                                validation_errors.append(
                                    f"Dependency '{dep_id}' failed or did not run."
                                )
                                continue
                            try:
                                value = self.resolve_nested_path(
                                    dep_result.output, output_key
                                )
                                context[placeholder] = value
                            except (KeyError, IndexError, TypeError) as exc:
                                validation_errors.append(
                                    f"Failed to resolve path '{output_key}' in dependency '{dep_id}': {exc}"
                                )
                        else:
                            context[placeholder] = mapping  # literal value

                if not getattr(node, "dependencies", []):
                    context.update(self.initial_context)

                if validation_errors:
                    error_msg = (
                        f"Node '{node.id}' context validation failed:\n"
                        + "\n".join(validation_errors)
                    )
                    logger.error(error_msg)
                    await self._trigger_callbacks("node_error", node_id, error_msg)
                    return node_id, NodeExecutionResult(
                        success=False,
                        error=error_msg,
                        metadata=self._create_error_metadata(
                            node, start_time, "ContextValidationError"
                        ),
                    )

                # -----------------------------------------------------------------
                # Notify callbacks – node_start
                # -----------------------------------------------------------------
                await self._trigger_callbacks("node_start", node_id, context)

                # -----------------------------------------------------------------
                # Cache lookup -----------------------------------------------------
                # -----------------------------------------------------------------
                cache_key = None
                if getattr(node.config, "use_cache", True):
                    try:
                        cache_key = self._make_cache_key(node.config, context)
                        if cache_key in self._cache:
                            cached_res = self._cache[cache_key]
                            logger.info("Cache hit for node '%s'", node.id)
                            return node_id, cached_res
                    except Exception:
                        # Never fail execution because of cache hashing issues.
                        cache_key = None

                # Execute -----------------------------------------------------------
                logger.debug(
                    f"Node '{node.id}' executing with context: {json.dumps(context, indent=2, default=str)}"
                )
                # Apply per-node timeout if configured ---------------------------------
                timeout_s = getattr(node.config, "timeout_seconds", None)
                try:
                    if timeout_s is not None:
                        result = await asyncio.wait_for(
                            node.execute(context), timeout=timeout_s
                        )
                    else:
                        result = await node.execute(context)
                except asyncio.TimeoutError:
                    error_msg = f"Node '{node.id}' timed out after {timeout_s} seconds"
                    logger.error(error_msg)
                    span.set_status(Status(StatusCode.ERROR, error_msg))
                    await self._trigger_callbacks("node_error", node_id, error_msg)
                    return node_id, NodeExecutionResult(
                        success=False,
                        error=error_msg,
                        metadata=self._create_error_metadata(
                            node, start_time, "TimeoutError"
                        ),
                    )

                # Normalise to NodeExecutionResult ---------------------------------
                if not isinstance(result, NodeExecutionResult):
                    if isinstance(result, dict):
                        result = NodeExecutionResult(
                            success=result.get("success", True),
                            output=result.get("output"),
                            error=result.get("error"),
                            metadata=self._create_error_metadata(node, start_time),
                        )
                    else:
                        result = NodeExecutionResult(
                            success=False,
                            error=f"Unexpected result type from node '{node.id}': {type(result)}",
                            metadata=self._create_error_metadata(
                                node, start_time, "UnexpectedResultTypeError"
                            ),
                        )

                # Put into cache ----------------------------------------------------
                if cache_key is not None and result.success:
                    self._cache[cache_key] = result

                # Persist + callbacks ----------------------------------------------
                if result.success and self.persist_intermediate_outputs:
                    payload = result.output

                    # Offload big payloads to artifact store ----------------------
                    if self.artifact_store is not None and payload is not None:
                        try:
                            raw = json.dumps(payload, default=str).encode()
                            if len(raw) > self.large_output_threshold:
                                ref = self.artifact_store.put(payload)
                                payload = {"artifact_ref": str(ref)}
                                logger.info(
                                    "Stored large output of node '%s' as artifact %s (size=%d bytes)",
                                    node_id,
                                    ref,
                                    len(raw),
                                )
                        except Exception as exc:  # noqa: BLE001 – best-effort offload
                            logger.warning(
                                "Artifact offload failed for node '%s': %s",
                                node_id,
                                exc,
                            )

                    self.context_manager.update_context(
                        node_id, payload, execution_id=self.chain_id
                    )

                # Callback for node_end will be triggered once below after all
                # post-processing (schema validation etc.) is complete to avoid
                # duplicate invocations.

                # Optional: enforce output schema post-execution -----------------
                if self.enforce_output_schema and result.success:
                    schema = getattr(node.config, "output_schema", None)
                    if schema is not None and schema != {}:
                        try:
                            from app.utils.type_coercion import coerce_types

                            coerce_types(result.output, schema)
                        except Exception as exc:
                            # Flip success flag and attach error information
                            result.success = False
                            result.error = f"Schema validation error: {exc}"
                            if result.metadata:
                                result.metadata.error_type = "SchemaValidationError"
                            logger.error(
                                "Schema validation failed for node '%s': %s",
                                node_id,
                                exc,
                            )

                span.set_attribute("success", result.success)
                if result.success:
                    # Successful execution – trigger end callbacks
                    await self._trigger_callbacks("node_end", node_id, result.output)
                else:
                    await self._trigger_callbacks(
                        "node_error", node_id, result.error or "unknown"
                    )
                    span.set_status(Status(StatusCode.ERROR, result.error or "unknown"))

                return node_id, result
            except Exception as exc:
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                logger.error(
                    "Unexpected error in execute_node",
                    node=node_id,
                    error=str(exc),
                    exc_info=True,
                )
                await self._trigger_callbacks("node_error", node_id, exc)
                return node_id, NodeExecutionResult(
                    success=False,
                    error=str(exc),
                    metadata=self._create_error_metadata(
                        node, start_time, exc.__class__.__name__
                    ),
                )

    # ---------------------------------------------------------------------
    # Helper utilities
    # ---------------------------------------------------------------------

    def _create_error_metadata(self, node, start_time, error_type="UnknownError"):
        return NodeMetadata(
            node_id=node.id,
            node_type=getattr(node, "type", "unknown"),
            start_time=start_time,
            end_time=datetime.utcnow(),
            error_type=error_type,
            provider=getattr(node, "provider", None),
        )

    async def _trigger_callbacks(
        self, event: str, node_id: str, payload: Any | None = None
    ) -> None:
        """Dispatch *event* to all registered callbacks.

        The local *ScriptChainCallback* interface expects three positional
        arguments for node-level events: ``chain_id``, ``node_id`` and a third
        value carrying either *inputs*, *outputs* or the *error* instance.  We
        forward the correct signature and transparently handle both synchronous
        and ``async`` callback implementations.
        """

        import inspect

        for callback in self.callbacks:
            try:
                if event == "node_start":
                    fn = getattr(callback, "on_node_start", None)
                    args = (self.chain_id, node_id, payload)
                elif event == "node_end":
                    fn = getattr(callback, "on_node_end", None)
                    args = (self.chain_id, node_id, payload)
                elif event == "node_error":
                    fn = getattr(callback, "on_node_error", None)
                    args = (self.chain_id, node_id, payload)
                else:
                    fn = None

                if fn is None:
                    continue

                result = fn(*args)  # type: ignore[misc]
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:  # pragma: no cover – callback failures shouldn't crash nodes
                logger.error(
                    "Error in callback %s during %s: %s",
                    callback.__class__.__name__,
                    event,
                    exc,
                )

    @staticmethod
    def resolve_nested_path(data: Any, path: str) -> Any:
        if not path or path == ".":
            return data
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                if part not in current:
                    raise KeyError(
                        f"Key '{part}' not found in dict. Available keys: {list(current.keys())}"
                    )
                current = current[part]
            elif isinstance(current, (list, tuple)):
                try:
                    index = int(part)
                    if index < 0 or index >= len(current):
                        raise IndexError(
                            f"Index {index} out of bounds for array of length {len(current)}"
                        )
                    current = current[index]
                except ValueError:
                    raise TypeError(
                        f"Cannot use non-integer key '{part}' to index array"
                    )
            else:
                raise TypeError(f"Cannot access '{part}' on type {type(current)}")
        return current

    # ---------------------------------------------------------------------
    # Cache key helper
    # ---------------------------------------------------------------------

    @staticmethod
    def _make_cache_key(config, context):  # noqa: D401
        import hashlib
        import json  # local import to avoid top-level cost

        dumped = json.dumps(
            {
                "config": config.model_dump(exclude={"metadata"}),
                "context": context,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(dumped.encode()).hexdigest()
