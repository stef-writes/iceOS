from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, cast

# ---------------------------------------------------------------------------
# Local type alias to satisfy static analysis on forward reference annotations.
# ---------------------------------------------------------------------------
from typing import Any as _Any

import structlog
from opentelemetry import trace  # type: ignore[import-not-found]
from opentelemetry.trace import Status, StatusCode  # type: ignore[import-not-found]

from ice_orchestrator.providers.budget_enforcer import BudgetEnforcer

# Import globally to avoid local shadowing errors
from ice_core.models import NodeConfig, NodeExecutionResult, NodeMetadata
from ice_sdk.registry.node import get_executor

# Local alias to avoid circular import; resolved at runtime
ScriptChain = _Any  # type: ignore[assignment]

if TYPE_CHECKING:  # pragma: no cover
    pass

tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)


class NodeExecutor:  # noqa: D101 – internal utility extracted from ScriptChain
    """Execute individual nodes with retry, caching & tracing.

    The implementation is **functionally identical** to the original logic in
    `ScriptChain.execute_node`.  It operates *through* a reference to the parent
    ScriptChain instance so that no behaviour changes are required elsewhere.
    """

    def __init__(self, chain: "ScriptChain") -> None:  # noqa: D401
        self.chain = chain
        self.budget = BudgetEnforcer()  # Add enforcer

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    # ------------------------------------------------------------------

    async def execute_node(
        self, node_id: str, input_data: Dict[str, Any]
    ) -> "NodeExecutionResult":
        """Delegate execution to the node registry while preserving all original
        orchestration semantics (cache, retries, validation, etc.)."""

        chain = self.chain  # local alias for brevity
        node = chain.nodes.get(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' not found in chain configuration")

        # ------------------------------------------------------------------
        # Rule 13 – idempotent validate() on every node ---------------------
        # ------------------------------------------------------------------

        try:
            node.runtime_validate()  # type: ignore[attr-defined]
        except Exception as exc:
            # models imported at module level – avoid re-importing inside function
            error_meta = NodeMetadata(  # type: ignore[call-arg]
                node_id=node_id,
                node_type=str(getattr(node, "type", "")),
                name=getattr(node, "name", None),
                version="1.0.0",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration=0.0,
                error_type=type(exc).__name__,
            )

            # Fail fast per FailurePolicy.HALT else return failure result ----
            if chain.failure_policy.name == "HALT":
                raise

            return NodeExecutionResult(  # type: ignore[call-arg]
                success=False,
                error=f"Validation failed for node '{node_id}': {exc}",
                metadata=error_meta,
            )

        # --------------------------------------------------------------
        # Persist *input_data* to the context store --------------------
        # --------------------------------------------------------------
        _ctx_cur = chain.context_manager.get_context()
        exec_id = _ctx_cur.execution_id if _ctx_cur is not None else None

        chain.context_manager.update_node_context(
            node_id=node_id,
            content=input_data,
            execution_id=exec_id,
        )

        max_retries: int = int(getattr(node, "retries", 0))
        base_backoff: float = float(getattr(node, "backoff_seconds", 0.0))

        attempt = 0
        last_error: Exception | None = None

        while attempt <= max_retries:
            try:
                # --------------------------------------------------
                # Cache lookup (opt-in) ----------------------------
                # --------------------------------------------------
                cache_key: str | None = None
                if chain.use_cache and getattr(node, "use_cache", True):
                    try:
                        from pydantic import BaseModel  # local import

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
                        cached = chain._cache.get(cache_key)
                        if cached is not None:
                            return cast(NodeExecutionResult, cached)
                    except Exception:  # noqa: BLE001 – never fail due to cache
                        cache_key = None

                # --------------------------------------------------
                # Dispatch to executor -----------------------------
                # --------------------------------------------------
                executor = get_executor(str(getattr(node, "type", "")))  # type: ignore[arg-type]

                with tracer.start_as_current_span(
                    "node.execute",
                    attributes={
                        "node_id": node_id,
                        "node_type": str(getattr(node, "type", "")),
                    },
                ) as node_span:
                    # MyPy may not recognise that *executor* is an async callable – cast for clarity.
                    from typing import Awaitable
                    from typing import cast as _cast

                    raw_output = await _cast(
                        Awaitable[Any],
                        executor(chain, node, input_data),
                    )

                    node_span.set_attribute(
                        "success", True
                    )  # Mark as success for now, validation will handle
                    node_span.set_attribute("retry_count", attempt)
                    if (
                        not raw_output
                    ):  # If executor returned None or empty, mark as failure
                        node_span.set_status(
                            Status(StatusCode.ERROR, "Executor returned empty output")
                        )
                        raw_output = (
                            None  # Ensure raw_output is None for further processing
                        )

                # --------------------------------------------------
                # Opportunistic JSON repair ------------------------
                # --------------------------------------------------
                if isinstance(raw_output, str) and getattr(node, "output_schema", None):
                    import re

                    raw = raw_output.strip()
                    if raw.startswith("```") and raw.endswith("```"):
                        raw = re.sub(r"^```.*?\n|\n```$", "", raw, count=1, flags=re.S)
                    try:
                        repaired = json.loads(raw)
                        raw_output = repaired  # type: ignore[assignment]
                    except Exception:
                        pass  # leave unchanged – validation will handle

                # New coercion layer
                processed_output = self._coerce_output(node, raw_output)

                # Store in cache if enabled & succeeded -------------
                if cache_key and processed_output is not None:
                    chain._cache.set(
                        cache_key,
                        NodeExecutionResult(success=True, output=processed_output),
                    )

                # ------------------------------------------------------------------
                # Apply *output_mappings* to make aliased keys available ----------
                # ------------------------------------------------------------------
                if (
                    True  # Always apply mappings if output is not None
                    and hasattr(node, "output_mappings")
                    and node.output_mappings
                ):
                    from ice_orchestrator.utils.context_builder import ContextBuilder

                    if isinstance(processed_output, dict):
                        for alias, src_path in node.output_mappings.items():  # type: ignore[attr-defined]
                            try:
                                value = ContextBuilder.resolve_nested_path(
                                    processed_output, src_path
                                )
                                # Add type validation
                                expected_type = (
                                    next(iter(node.output_schema.values()), None)
                                    if node.output_schema
                                    else None
                                )
                                if expected_type and not isinstance(
                                    value, expected_type
                                ):
                                    raise TypeError(
                                        f"Expected {expected_type} for path '{src_path}', got {type(value)}"
                                    )
                                processed_output[alias] = value
                            except Exception:
                                # Ignore unresolved paths – validation will catch downstream
                                continue

                # Attach retry metadata -----------------------------
                if processed_output:  # Only update if output was processed
                    result = NodeExecutionResult(success=True, output=processed_output)
                    result.metadata = NodeMetadata(
                        node_id=node_id,
                        node_type=str(getattr(node, "type", "")),
                        name=getattr(node, "name", None),
                        version="1.0.0",
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        duration=0.0,
                        error_type=None,
                        retry_count=attempt,
                    )
                    result.budget_status = self.budget.get_status()  # Add this field

                    # Persist *output* to context store ------------------
                    if (
                        chain.persist_intermediate_outputs
                        and processed_output is not None
                    ):
                        # Safe retrieval of *execution_id* from optional context
                        _ctx_latest = chain.context_manager.get_context()
                        latest_exec_id = (
                            _ctx_latest.execution_id if _ctx_latest else None
                        )

                        chain.context_manager.update_node_context(
                            node_id=node_id,
                            content=processed_output,
                            execution_id=latest_exec_id,
                        )

                    # Optional output validation ------------------------
                    if chain.validate_outputs and getattr(node, "output_schema", None):
                        from ice_orchestrator.validation import SchemaValidator

                        if not SchemaValidator().is_output_valid(
                            node, processed_output
                        ):
                            result.success = False
                            err_msg = f"Output validation failed for node '{node_id}' against declared schema"
                            result.error = (
                                err_msg
                                if result.error is None
                                else result.error + "; " + err_msg
                            )

                    # Add budget tracking
                    if node.type == "ai":
                        cost = (
                            getattr(result.usage, "cost", 0.0) if result.usage else 0.0
                        )
                        self.budget.register_llm_call(cost=cost)
                    elif node.type == "tool":
                        self.budget.register_tool_execution()

                    return result

                else:  # If output was None after all processing, return failure
                    result = NodeExecutionResult(
                        success=False, error="Executor returned empty output"
                    )
                    result.metadata = NodeMetadata(
                        node_id=node_id,
                        node_type=str(getattr(node, "type", "")),
                        name=getattr(node, "name", None),
                        version="1.0.0",
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        duration=0.0,
                        error_type=(
                            type(last_error).__name__ if last_error else "UnknownError"
                        ),
                        retry_count=attempt,
                    )
                    result.budget_status = self.budget.get_status()
                    return result

            except Exception as exc:  # pylint: disable=broad-except
                last_error = exc
                if attempt >= max_retries:
                    break

                wait_seconds = base_backoff * (2**attempt) if base_backoff > 0 else 0
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)

                attempt += 1

        # --------------------------------------------------------------
        # All retries exhausted – build failure result -----------------
        # --------------------------------------------------------------
        # models imported at module level – avoid re-importing inside function
        error_meta = NodeMetadata(  # type: ignore[call-arg]
            node_id=node_id,
            node_type=str(getattr(node, "type", "")),
            name=getattr(node, "name", None),
            version="1.0.0",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration=0.0,
            error_type=type(last_error).__name__ if last_error else "UnknownError",
            retry_count=attempt,
        )

        if chain.failure_policy.name == "HALT":  # safeguard – avoid circular import
            raise last_error if last_error else Exception("Unknown error")

        return NodeExecutionResult(  # type: ignore[call-arg]
            success=False,
            error=f"Retry limit exceeded ({max_retries}) – last error: {last_error}",
            metadata=error_meta,
        )

    def _coerce_output(self, node: NodeConfig, raw_output: Any) -> Any:
        if not node.output_schema:
            return raw_output

        if isinstance(node.output_schema, dict):
            # Handle simple type conversions
            expected_type = next(iter(node.output_schema.values()), None)
            if expected_type is int:
                return int(raw_output)
            elif expected_type is float:
                return float(raw_output)
            # Add other types as needed

        return raw_output
