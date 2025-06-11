"""Execution helper responsible for running individual workflow nodes.

This module was extracted from the original *level_based_script_chain.py* to
reduce file size and to improve test-ability.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import structlog
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.chains.orchestration.workflow_execution_context import (
    WorkflowExecutionContext,
)
from app.models.node_models import InputMapping, NodeExecutionResult, NodeMetadata
from app.utils.artifact_store import ArtifactStore

# ---------------------------------------------------------------------------
# Tracing & logging setup ----------------------------------------------------
# ---------------------------------------------------------------------------
tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)


class NodeExecutor:  # noqa: D101 – public class, docstring in module preamble
    """Executes a single workflow *node* inside a ScriptChain."""

    def __init__(
        self,
        context_manager: Any,
        chain_id: str,
        *,
        persist_intermediate_outputs: bool = True,
        callbacks: Optional[List[Any]] = None,
        tool_service: Optional[Any] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[WorkflowExecutionContext] = None,
        artifact_store: Optional[ArtifactStore] = None,
        large_output_threshold: int = 256 * 1024,  # 256 KiB
        cache: Optional[dict[str, NodeExecutionResult]] = None,
        enforce_output_schema: bool = True,
    ) -> None:
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

    # ---------------------------------------------------------------------
    # Public API -----------------------------------------------------------
    # ---------------------------------------------------------------------
    async def execute_node(
        self, node: Any, accumulated_results: Dict[str, NodeExecutionResult]
    ) -> Tuple[str, NodeExecutionResult]:
        """Run *node* and return its :class:`NodeExecutionResult`."""

        start_time = datetime.utcnow()
        node_id = node.id

        # --------------------------- OpenTelemetry span -------------------
        with tracer.start_as_current_span(
            "node.execute",
            attributes={"node_id": node_id, "chain_id": self.chain_id},
        ) as span:
            try:
                # ----------------------------------------------------------
                # Build context & validate prerequisites
                # ----------------------------------------------------------
                context: Dict[str, Any] = {}
                validation_errors: List[str] = []

                if getattr(node, "input_mappings", None):
                    for placeholder, mapping in node.input_mappings.items():
                        # mapping can either be an *InputMapping* or a literal value.
                        is_reference = isinstance(mapping, InputMapping) or (
                            isinstance(mapping, dict)
                            and "source_node_id" in mapping
                            and "source_output_key" in mapping
                        )

                        if is_reference:
                            # Normalise dict → *InputMapping* -----------------
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
                        f"Node '{node.id}' context validation failed:\n" + "\n".join(validation_errors)
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

                # ----------------------------------------------------------
                # Notify callbacks – node_start
                # ----------------------------------------------------------
                await self._trigger_callbacks("node_start", node_id, context)

                # ----------------------------------------------------------
                # Cache lookup --------------------------------------------
                # ----------------------------------------------------------
                cache_key: Optional[str] = None
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

                # ----------------------------------------------------------
                # Execute node --------------------------------------------
                # ----------------------------------------------------------
                logger.debug(
                    "Node '%s' executing with context: %s",
                    node.id,
                    json.dumps(context, indent=2, default=str),
                )
                timeout_s = getattr(node.config, "timeout_seconds", None)
                try:
                    if timeout_s is not None:
                        result = await asyncio.wait_for(node.execute(context), timeout=timeout_s)
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
                        metadata=self._create_error_metadata(node, start_time, "TimeoutError"),
                    )

                # ----------------------------------------------------------
                # Normalise result ----------------------------------------
                # ----------------------------------------------------------
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
                            metadata=self._create_error_metadata(node, start_time, "UnexpectedResultTypeError"),
                        )

                # ----------------------------------------------------------
                # Update cache -------------------------------------------
                # ----------------------------------------------------------
                if cache_key is not None and result.success:
                    self._cache[cache_key] = result

                # ----------------------------------------------------------
                # Persist intermediate outputs ---------------------------
                # ----------------------------------------------------------
                if result.success and self.persist_intermediate_outputs:
                    payload = result.output

                    # Offload large payloads ------------------------------
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
                        except Exception as exc:  # noqa: BLE001 – best effort offload
                            logger.warning("Artifact offload failed for node '%s': %s", node_id, exc)

                    self.context_manager.update_context(node_id, payload, execution_id=self.chain_id)

                # ----------------------------------------------------------
                # Optional schema validation -----------------------------
                # ----------------------------------------------------------
                if self.enforce_output_schema and result.success:
                    schema = getattr(node.config, "output_schema", None)
                    if schema is not None and schema != {}:
                        try:
                            from app.utils.type_coercion import coerce_types

                            coerce_types(result.output, schema)
                        except Exception as exc:
                            result.success = False
                            result.error = f"Schema validation error: {exc}"
                            if result.metadata:
                                result.metadata.error_type = "SchemaValidationError"
                            logger.error(
                                "Schema validation failed for node '%s': %s",
                                node_id,
                                exc,
                            )

                # ----------------------------------------------------------
                # Callbacks / span status ---------------------------------
                # ----------------------------------------------------------
                span.set_attribute("success", result.success)
                if result.success:
                    await self._trigger_callbacks("node_end", node_id, result.output)
                else:
                    await self._trigger_callbacks("node_error", node_id, result.error or "unknown")
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
                    metadata=self._create_error_metadata(node, start_time, exc.__class__.__name__),
                )

    # ---------------------------------------------------------------------
    # Helper utilities -----------------------------------------------------
    # ---------------------------------------------------------------------

    def _create_error_metadata(self, node: Any, start_time: datetime, error_type: str = "UnknownError") -> NodeMetadata:
        return NodeMetadata(
            node_id=node.id,
            node_type=getattr(node, "type", "unknown"),
            start_time=start_time,
            end_time=datetime.utcnow(),
            error_type=error_type,
            provider=getattr(node, "provider", None),
        )

    async def _trigger_callbacks(self, event: str, node_id: str, payload: Any | None = None) -> None:  # noqa: D401 – docstring below
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
                logger.error("Error in callback %s during %s: %s", callback.__class__.__name__, event, exc)

    # ---------------------------------------------------------------------
    # Static helpers -------------------------------------------------------
    # ---------------------------------------------------------------------

    @staticmethod
    def resolve_nested_path(data: Any, path: str) -> Any:  # noqa: D401 – tiny util
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
                    raise TypeError(f"Cannot use non-integer key '{part}' to index array")
            else:
                raise TypeError(f"Cannot access '{part}' on type {type(current)}")
        return current

    @staticmethod
    def _make_cache_key(config: Any, context: Dict[str, Any]) -> str:  # noqa: D401 – tiny util
        import hashlib
        import json as _json  # local import to avoid top-level cost

        dumped = _json.dumps(
            {
                "config": config.model_dump(exclude={"metadata"}),
                "context": context,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(dumped.encode()).hexdigest() 