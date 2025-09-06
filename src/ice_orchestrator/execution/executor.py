from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime

# ---------------------------------------------------------------------------
# Local type alias to satisfy static analysis on forward reference annotations.
# ---------------------------------------------------------------------------
from typing import TYPE_CHECKING, Any, Dict, cast

import structlog

try:
    from opentelemetry import trace  # type: ignore[import-not-found]
    from opentelemetry.trace import Status, StatusCode  # type: ignore[import-not-found]
except Exception:  # pragma: no cover – optional telemetry

    class _NoopSpan:
        def set_attribute(self, *args, **kwargs):
            return None

        def set_status(self, *args, **kwargs):
            return None

        def end(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _NoopTracer:
        def start_as_current_span(self, *args, **kwargs):
            return _NoopSpan()

    class _NoopTrace:
        def get_tracer(self, *args, **kwargs):
            return _NoopTracer()

    trace = _NoopTrace()  # type: ignore

    class Status:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            pass

    class StatusCode:  # type: ignore
        ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Ensure built-in node executors are registered *before* any workflow runs.
# Merely importing these modules triggers the @register_node decorators.
# ---------------------------------------------------------------------------
# ruff: noqa: F401 – imported for side-effects only
import ice_orchestrator.execution.executors  # Import for side effects

# Import globally to avoid local shadowing errors
from ice_core.models import NodeConfig, NodeExecutionResult
from ice_core.models.node_models import NodeMetadata
from ice_core.unified_registry import get_executor
from ice_orchestrator.providers.budget_enforcer import BudgetEnforcer

if TYPE_CHECKING:  # pragma: no cover
    from ice_orchestrator.workflow import Workflow

tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)


class NodeExecutor:  # – internal utility extracted from ScriptChain
    """Execute individual nodes with retry, caching & tracing.

    The implementation is **functionally identical** to the original logic in
    `ScriptChain.execute_node`.  It operates *through* a reference to the parent
    ScriptChain instance so that no behaviour changes are required elsewhere.
    """

    def __init__(self, chain: "Workflow") -> None:
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
        # Emit start event via async handler when available
        try:
            from ice_orchestrator.execution.workflow_events import (
                NodeStarted as _NodeStarted,
            )

            wf_id = str(getattr(chain, "chain_id", ""))
            run_id = str(getattr(chain, "run_id", ""))
            await chain._event_handler.emit(
                _NodeStarted(  # type: ignore[attr-defined]
                    workflow_id=wf_id,
                    run_id=run_id,
                    node_id=node_id,
                    node_run_id=f"{run_id}_{node_id}",
                )
            )
        except Exception:
            pass
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
                owner="system",
                description=f"Node {node_id} validation failed",
                provider=getattr(node, "provider", None),
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

        # Store input data but ensure it's serializable
        # Skip storing inputs as they may contain NodeExecutionResult objects
        # The actual output will be stored after execution in workflow.py
        pass  # Removed input storage to prevent serialization errors

        # ------------------------------------------------------------------
        # Retry policy extraction (v2) --------------------------------------
        # ------------------------------------------------------------------

        policy = getattr(node, "retry_policy", None)
        base_backoff: float
        if policy is not None:
            # New structured policy overrides legacy scalar fields
            max_retries = (
                int(getattr(policy, "max_attempts", 1)) - 1
            )  # attempts after first run
            base_backoff = float(getattr(policy, "backoff_seconds", 0.0))
            backoff_strategy = str(getattr(policy, "backoff_strategy", "exponential"))
        else:
            max_retries = int(getattr(node, "retries", 0))
            base_backoff = float(getattr(node, "backoff_seconds", 0.0))
            backoff_strategy = "exponential"

        from ice_core.metrics import EXEC_FAILED

        def _calc_backoff(idx: int) -> float:
            if base_backoff <= 0:
                return 0.0
            if backoff_strategy == "fixed":
                return base_backoff
            if backoff_strategy == "linear":
                return base_backoff * idx
            # exponential (default)
            return float(base_backoff * (2**idx))

        last_error: Exception | None = None
        result_raw: Any | None = None

        for attempt in range(max_retries + 1):
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
                    except Exception:  # – never fail due to cache
                        cache_key = None

                # --------------------------------------------------
                # Dispatch to executor with retry ------------------
                # --------------------------------------------------
                for attempt in range(max_retries + 1):
                    try:
                        executor = get_executor(str(getattr(node, "type", "")))  # type: ignore[arg-type]

                        with tracer.start_as_current_span(
                            "node.execute",
                            attributes={
                                "node_id": node_id,
                                "node_type": str(getattr(node, "type", "")),
                            },
                        ):
                            import os as _os

                            from ice_orchestrator.execution.sandbox.resource_sandbox import (
                                ResourceSandbox,
                            )

                            timeout = getattr(node, "timeout_seconds", 30) or 30
                            # Generic overrides with per-type fallbacks
                            _kind = str(getattr(node, "type", ""))
                            _mem_env = {
                                "tool": "ICE_SANDBOX_TOOL_MEMORY_MB",
                                "code": "ICE_SANDBOX_CODE_MEMORY_MB",
                                "agent": "ICE_SANDBOX_AGENT_MEMORY_MB",
                                "llm": "ICE_SANDBOX_LLM_MEMORY_MB",
                            }.get(_kind, "ICE_SANDBOX_DEFAULT_MEMORY_MB")
                            _cpu_env = {
                                "tool": "ICE_SANDBOX_TOOL_CPU_SECONDS",
                                "code": "ICE_SANDBOX_CODE_CPU_SECONDS",
                                "agent": "ICE_SANDBOX_AGENT_CPU_SECONDS",
                                "llm": "ICE_SANDBOX_LLM_CPU_SECONDS",
                            }.get(_kind, "ICE_SANDBOX_DEFAULT_CPU_SECONDS")
                            _mem_mb = int(
                                _os.getenv(
                                    _mem_env,
                                    _os.getenv("ICE_SANDBOX_DEFAULT_MEMORY_MB", "512"),
                                )
                            )
                            _cpu_s = int(
                                _os.getenv(
                                    _cpu_env,
                                    _os.getenv("ICE_SANDBOX_DEFAULT_CPU_SECONDS", "10"),
                                )
                            )

                            async with ResourceSandbox(
                                timeout_seconds=timeout,
                                memory_limit_mb=_mem_mb,
                                cpu_limit_seconds=_cpu_s,
                            ) as sbx:
                                result_raw = await sbx.run_with_timeout(
                                    executor(chain, node, input_data)
                                )
                        break  # success
                    except Exception as exc:
                        last_error = exc  # remember last
                        if attempt == max_retries:
                            from ice_core.metrics import EXEC_FAILED

                            EXEC_FAILED.inc()
                            raise
                        await asyncio.sleep(_calc_backoff(attempt))
                    # --------------------------------------------------

                # --------------------------------------------------
                # If executor returned a NodeExecutionResult, preserve it ----
                # --------------------------------------------------
                from ice_core.models import NodeExecutionResult as _NER  # local import

                if isinstance(result_raw, _NER):
                    # Budget accounting before returning
                    if node.type == "llm":
                        cost = (
                            getattr(result_raw.usage, "cost", 0.0)
                            if getattr(result_raw, "usage", None)
                            else 0.0
                        )
                        self.budget.register_llm_call(cost=cost)
                    elif node.type == "agent":
                        cost = (
                            getattr(result_raw.usage, "cost", 0.0)
                            if getattr(result_raw, "usage", None)
                            else 0.0
                        )
                        self.budget.register_agent_call(cost=cost)
                    elif node.type == "tool":
                        self.budget.register_tool_execution()
                    elif node.type == "workflow":
                        self.budget.register_workflow_execution()
                    elif node.type == "code":
                        self.budget.register_code_execution()
                    # Best-effort minimal context persistence to avoid regressions
                    from ice_core.exceptions import (
                        SerializationError as _SerErr,  # local import
                    )

                    _ctx_latest = chain.context_manager.get_context()
                    latest_exec_id = _ctx_latest.execution_id if _ctx_latest else None
                    minimal_content: Any = result_raw.output
                    try:
                        if node.type == "llm" and isinstance(result_raw.output, dict):

                            def _trim(val: Any, max_chars: int = 1500) -> Any:
                                if isinstance(val, str) and len(val) > max_chars:
                                    return val[:max_chars]
                                return val

                            if "text" in result_raw.output and isinstance(
                                result_raw.output["text"], str
                            ):
                                minimal_content = {
                                    "text": _trim(result_raw.output["text"])
                                }
                            elif "response" in result_raw.output and isinstance(
                                result_raw.output["response"], str
                            ):
                                minimal_content = {
                                    "text": _trim(result_raw.output["response"])
                                }
                            else:
                                minimal_content = {
                                    "text": _trim(str(result_raw.output))
                                }
                    except Exception:
                        minimal_content = result_raw.output

                    try:
                        chain.context_manager.update_node_context(
                            node_id=node_id,
                            content=minimal_content,
                            execution_id=latest_exec_id,
                        )
                    except _SerErr:
                        pass
                    except Exception:
                        pass
                    # Attach context and rendered prompt preview when possible
                    try:
                        # Expose keys used (roots) and a safe prompt preview if present
                        ctx_keys = list(input_data.keys())
                        if isinstance(result_raw.output, dict):
                            result_raw.context_used = {
                                "available_roots": ctx_keys,
                            }
                        # Rendered prompt preview is executor-specific; attach best-effort
                        if node.type == "llm":
                            # Best-effort: if output contains a 'prompt' echo or 'rendered_prompt', expose preview
                            preview = None
                            for key in ("rendered_prompt", "prompt", "input_prompt"):
                                if key in (result_raw.output or {}):
                                    preview = str((result_raw.output or {}).get(key))
                                    break
                            if preview:
                                if len(preview) > 1200:
                                    preview = preview[:1200] + "…"
                                setattr(result_raw, "rendered_prompt_preview", preview)
                    except Exception:
                        pass
                    return result_raw

                # --------------------------------------------------
                # Preserve executor-provided NodeExecutionResult ----
                # (after inner retry loop completes)
                # --------------------------------------------------
                from ice_core.models import NodeExecutionResult as _NER

                if isinstance(result_raw, _NER):
                    # Budget accounting before returning
                    if node.type == "llm":
                        cost = (
                            getattr(result_raw.usage, "cost", 0.0)
                            if getattr(result_raw, "usage", None)
                            else 0.0
                        )
                        self.budget.register_llm_call(cost=cost)
                    elif node.type == "agent":
                        cost = (
                            getattr(result_raw.usage, "cost", 0.0)
                            if getattr(result_raw, "usage", None)
                            else 0.0
                        )
                        self.budget.register_agent_call(cost=cost)
                    elif node.type == "tool":
                        self.budget.register_tool_execution()
                    elif node.type == "workflow":
                        self.budget.register_workflow_execution()
                    elif node.type == "code":
                        self.budget.register_code_execution()

                    return result_raw

                # --------------------------------------------------
                # Opportunistic JSON repair ------------------------
                # --------------------------------------------------
                if isinstance(result_raw, str) and getattr(node, "output_schema", None):
                    import re

                    raw = result_raw.strip()
                    if raw.startswith("```") and raw.endswith("```"):
                        raw = re.sub(r"^```.*?\n|\n```$", "", raw, count=1, flags=re.S)
                    try:
                        repaired = json.loads(raw)
                        result_raw = repaired  # type: ignore[assignment]
                    except Exception:
                        pass  # leave unchanged – validation will handle

                # Unwrap NodeExecutionResult to its semantic output first
                from ice_core.models import NodeExecutionResult as _NER

                if isinstance(result_raw, _NER):
                    raw_out = result_raw.output
                else:
                    raw_out = result_raw

                # New coercion layer + serialization safety
                processed_output = self._coerce_output(node, raw_out)
                # Guarantee JSON-serialisability for context persistence
                try:
                    json.dumps(processed_output, default=str)
                except Exception:
                    # Wrap non-serialisable outputs into a string repr
                    processed_output = json.loads(
                        json.dumps(processed_output, default=str)
                    )

                # Store in cache if enabled & succeeded -------------
                # (Cache write elided for now)

                # Emit finished event via async handler when available
                try:
                    from ice_orchestrator.execution.workflow_events import (
                        NodeCompleted as _NodeCompleted,
                    )

                    wf_id = str(getattr(chain, "chain_id", ""))
                    run_id = str(getattr(chain, "run_id", ""))
                    await chain._event_handler.emit(
                        _NodeCompleted(  # type: ignore[attr-defined]
                            workflow_id=wf_id,
                            run_id=run_id,
                            node_id=node_id,
                            node_run_id=f"{run_id}_{node_id}",
                            # duration_seconds will be recorded by handler/sink; include minimal metadata here
                        )
                    )
                except Exception:
                    pass

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
                                expected_type = None
                                if isinstance(
                                    getattr(node, "output_schema", None), dict
                                ):  # type: ignore[attr-defined]
                                    schema_dict = node.output_schema  # type: ignore[attr-defined]
                                    if schema_dict and isinstance(schema_dict, dict):
                                        expected_type = next(
                                            iter(schema_dict.values()), None
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
                    result = NodeExecutionResult(  # type: ignore[call-arg]
                        success=True,
                        output=processed_output,
                        metadata=NodeMetadata(  # type: ignore[call-arg]
                            node_id=node_id,
                            node_type=str(getattr(node, "type", "")),
                            name=getattr(node, "name", None),
                            version="1.0.0",
                            start_time=datetime.utcnow(),
                            end_time=datetime.utcnow(),
                            duration=0.0,
                            owner="system",
                            description=f"Node {node_id} execution result",
                            provider=getattr(node, "provider", None),
                            error_type=None,
                        ),
                        execution_time=0.0,
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

                        # Trim non-essential large fields for LLM nodes to avoid
                        # strict serializer oversize errors in context storage.
                        content_to_persist = processed_output
                        try:
                            if node.type == "llm" and isinstance(
                                processed_output, dict
                            ):
                                # Persist a minimal, size-safe view of LLM output
                                def _trim(val: Any, max_chars: int = 1500) -> Any:
                                    if isinstance(val, str) and len(val) > max_chars:
                                        return val[:max_chars]
                                    return val

                                if "text" in processed_output and isinstance(
                                    processed_output["text"], str
                                ):
                                    content_to_persist = {
                                        "text": _trim(processed_output["text"])
                                    }
                                elif "response" in processed_output and isinstance(
                                    processed_output["response"], str
                                ):
                                    content_to_persist = {
                                        "text": _trim(processed_output["response"])
                                    }
                                else:
                                    content_to_persist = {
                                        "text": _trim(str(processed_output))
                                    }
                        except Exception:
                            content_to_persist = processed_output

                        chain.context_manager.update_node_context(
                            node_id=node_id,
                            content=content_to_persist,
                            execution_id=latest_exec_id,
                        )

                    # Optional output validation ------------------------
                    if chain.validate_outputs and getattr(node, "output_schema", None):
                        from ice_core.validation import SchemaValidator

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
                    if node.type == "llm" or node.type == "agent":
                        cost = (
                            getattr(result.usage, "cost", 0.0) if result.usage else 0.0
                        )
                        if node.type == "llm":
                            self.budget.register_llm_call(cost=cost)
                        else:  # agent
                            self.budget.register_agent_call(cost=cost)
                    elif node.type == "tool":
                        self.budget.register_tool_execution()
                    elif node.type == "workflow":
                        self.budget.register_workflow_execution()
                    elif node.type == "code":
                        self.budget.register_code_execution()
                    # Note: condition, loop, and parallel are orchestration nodes that don't need budget tracking

                    return result

                else:  # If output was None after all processing, return failure
                    result = NodeExecutionResult(  # type: ignore[call-arg]
                        success=False,
                        error="Executor returned empty output",
                        metadata=NodeMetadata(  # type: ignore[call-arg]
                            node_id=node_id,
                            node_type=str(getattr(node, "type", "")),
                            name=getattr(node, "name", None),
                            version="1.0.0",
                            start_time=datetime.utcnow(),
                            end_time=datetime.utcnow(),
                            duration=0.0,
                            error_type=(
                                type(last_error).__name__
                                if last_error
                                else "UnknownError"
                            ),
                            owner="system",
                            description=f"Node {node_id} returned empty output",
                            provider=getattr(node, "provider", None),
                        ),
                    )
                    result.budget_status = self.budget.get_status()
                    return result

            except Exception as exc:  # pylint: disable=broad-except
                last_error = exc
                if attempt >= max_retries:
                    break

                # Emit retrying event via async handler (best-effort)
                try:
                    from ice_orchestrator.execution.workflow_events import (
                        NodeFailed as _FailEvt,
                    )

                    wf_id = str(getattr(chain, "chain_id", ""))
                    run_id = str(getattr(chain, "run_id", ""))
                    await chain._event_handler.emit(
                        _FailEvt(  # type: ignore[attr-defined]
                            workflow_id=wf_id,
                            run_id=run_id,
                            node_id=node_id,
                            error_type=type(exc).__name__,
                            error_message=str(exc),
                            retry_attempt=attempt + 1,
                            will_retry=True,
                        )
                    )
                except Exception:
                    pass

                if base_backoff <= 0:
                    wait_seconds: float = 0.0
                else:
                    if backoff_strategy == "fixed":
                        wait_seconds = base_backoff
                    elif backoff_strategy == "linear":
                        wait_seconds = base_backoff * (attempt + 1)
                    else:  # exponential default
                        wait_seconds = base_backoff * (2**attempt)

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
            owner="system",
            description=f"Node {node_id} retry limit exceeded",
            provider=getattr(node, "provider", None),
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
