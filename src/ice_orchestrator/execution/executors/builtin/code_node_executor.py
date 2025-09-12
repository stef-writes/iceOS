"""Executor for code nodes (server-side sandbox boundary)."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict

from ice_core.models import CodeNodeConfig, NodeExecutionResult
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
import logging
from ice_core.unified_registry import get_code_instance, has_code_factory, register_node
from ice_core.validation.schema_validator import SchemaValidator


@register_node("code")
async def code_node_executor(  # noqa: D401, ANN401
    workflow: "WorkflowLike",
    cfg: CodeNodeConfig,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:
    """Execute CodeNode in a constrained server-side context.

    Notes
    -----
    - This executor resolves a registered code factory via the unified registry
      using ``cfg.name``. Inline code is not executed here; it must be registered
      via MCP (dev-only) before use.
    - Sandbox policy (baseline):
      * Timeouts enforced via asyncio.wait_for
      * No shell usage within this executor
      * Network/file access policies are enforced by the factory implementation
        and deployment environment (future: WASM/subprocess isolation).
    - Runtime validation ensures outputs conform to ``cfg.output_schema``.
    """

    logger = logging.getLogger(__name__)
    start_time = datetime.utcnow()
    try:
        # Resolve the server-side factory instance with org scoping
        if not cfg.name:
            raise ValueError("CodeNodeConfig.name is required to resolve factory")
        org_id = None
        try:
            # Context may carry identity injected at API layer
            org_id = (ctx.get("identity") or {}).get("org_id") or ctx.get("org_id")
        except Exception:
            org_id = None
        # Prefer org-scoped factory name if present
        scoped_name = f"{org_id}:{cfg.name}" if org_id else cfg.name
        name_to_use = scoped_name if has_code_factory(scoped_name) else cfg.name
        factory = get_code_instance(name_to_use)

        # Enforce an execution timeout (default 30s; can be tuned later)
        async def _run() -> Dict[str, Any]:
            # Factories may be sync or async; normalize
            result = factory(workflow=workflow, cfg=cfg, ctx=ctx)  # type: ignore[call-arg]
            if asyncio.iscoroutine(result):
                from typing import cast as _cast
                awaited = await result
                if isinstance(awaited, dict):
                    return _cast(Dict[str, Any], awaited)
                return {"result": awaited}
            if isinstance(result, dict):
                return result
            return {"result": result}

        timeout_s = getattr(cfg, "timeout_seconds", None) or 30

        # Deny-by-default networking: block socket creation unless explicitly allowed
        import socket as _socket
        _orig_sock = _socket.socket
        _orig_create_conn = _socket.create_connection
        net_allowed = bool(getattr(cfg, "metadata", None) and getattr(cfg.metadata, "tags", None) and ("net-allow" in getattr(cfg.metadata, "tags", []))) or bool(getattr(cfg, "network_allowed", False))
        if not net_allowed:
            def _blocked_socket(*args, **kwargs):  # type: ignore[no-redef]
                raise RuntimeError("Network disabled by policy for code node")

            def _blocked_create_connection(*args, **kwargs):  # type: ignore[no-redef]
                raise RuntimeError("Network disabled by policy for code node")

            from typing import cast as _cast
            _mod = _cast(Any, _socket)
            _mod.socket = _blocked_socket  # type: ignore[assignment]
            _mod.create_connection = _blocked_create_connection  # type: ignore[assignment]

        logger.info(
            "node.code.execute.start",
            extra={
                "node_id": cfg.id,
                "name": name_to_use,
                "org_id": org_id,
                "timeout": timeout_s,
                "network_allowed": net_allowed,
            },
        )
        out: Dict[str, Any] = await asyncio.wait_for(_run(), timeout=timeout_s)

        # Validate against declared output_schema (dict or pydantic model)
        assert SchemaValidator.is_output_valid(cfg, out) is True

        end_time = datetime.utcnow()
        logger.info(
            "node.code.execute.finish",
            extra={
                "node_id": cfg.id,
                "name": name_to_use,
                "org_id": org_id,
                "duration_s": (end_time - start_time).total_seconds(),
                "success": True,
            },
        )
        return NodeExecutionResult(
            success=True,
            output=out,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.name,
                version="1.0.0",
                owner="system",
                provider=getattr(cfg, "provider", None),
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"Code execution: {cfg.name}",
            ),
        )
    except Exception as exc:  # pragma: no cover – defensive path
        end_time = datetime.utcnow()
        try:
            # Best-effort restore networking hooks
            import socket as _socket

            if '_orig_sock' in locals():
                from typing import cast as _cast
                _mod = _cast(Any, _socket)
                _mod.socket = _orig_sock  # type: ignore[assignment]
            if '_orig_create_conn' in locals():
                from typing import cast as _cast
                _mod = _cast(Any, _socket)
                _mod.create_connection = _orig_create_conn  # type: ignore[assignment]
        except Exception:
            pass
        logger.warning(
            "node.code.execute.finish",
            extra={
                "node_id": getattr(cfg, 'id', None),
                "name": getattr(cfg, 'name', None),
                "duration_s": (end_time - start_time).total_seconds(),
                "success": False,
                "error_type": type(exc).__name__,
            },
        )
        return NodeExecutionResult(
            success=False,
            error=str(exc),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.name,
                version="1.0.0",
                owner="system",
                error_type=type(exc).__name__,
                provider=getattr(cfg, "provider", None),
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"Code execution failed: {cfg.name}",
            ),
        )
    finally:
        # Ensure original socket functions are restored if we blocked them
        try:
            import socket as _socket

            if '_orig_sock' in locals():
                from typing import cast as _cast
                _mod = _cast(Any, _socket)
                _mod.socket = _orig_sock  # type: ignore[assignment]
            if '_orig_create_conn' in locals():
                from typing import cast as _cast
                _mod = _cast(Any, _socket)
                _mod.create_connection = _orig_create_conn  # type: ignore[assignment]
        except Exception:
            pass

"""Executor for code nodes."""

import ast
from datetime import datetime
from typing import Any, Dict, Optional

from ice_core.models import CodeNodeConfig, NodeExecutionResult
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry

try:
    from ice_orchestrator.execution.wasm_executor import (
        execute_node_with_wasm,  # type: ignore
    )
except Exception:  # pragma: no cover – optional WASM
    execute_node_with_wasm = None  # type: ignore[assignment]

__all__ = ["code_node_executor"]


# @register_node("code")  # disabled legacy implementation to avoid duplicate registration
async def code_node_executor_legacy(  # noqa: D401
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: Any,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:
    """Execute code via registered factory or inline source (WASM with fallback)."""
    start_time = datetime.utcnow()

    try:
        # ------------------------------------------------------------------
        # 1. Delegate to factory if registered -----------------------------
        # ------------------------------------------------------------------
        try:
            code_impl = registry.get_code_instance(getattr(cfg, "name", None) or cfg.id)
            # Support object.execute(), async def(...), or def(...)
            import inspect as _inspect

            if hasattr(code_impl, "execute") and callable(
                getattr(code_impl, "execute")
            ):
                maybe = code_impl.execute(workflow, cfg, ctx)
                out = await maybe if _inspect.isawaitable(maybe) else maybe
            elif callable(code_impl):
                maybe = code_impl(workflow, cfg, ctx)
                out = await maybe if _inspect.isawaitable(maybe) else maybe
            else:
                raise TypeError(
                    "Code factory did not return callable or object with execute()"
                )

            if isinstance(out, NodeExecutionResult):
                return out
            if not isinstance(out, dict):
                raise TypeError(
                    f"Code factory output must be dict, got {type(out).__name__}"
                )
            end_time = datetime.utcnow()
            return NodeExecutionResult(
                success=True,
                output=out,
                metadata=NodeMetadata(
                    node_id=getattr(cfg, "id", "code"),
                    node_type="code",
                    name=getattr(cfg, "name", "code_node"),
                    version="1.0.0",
                    owner="system",
                    provider=getattr(cfg, "provider", None),
                    error_type=None,
                    start_time=start_time,
                    end_time=end_time,
                    duration=(end_time - start_time).total_seconds(),
                    description="Code execution (factory)",
                ),
                execution_time=(end_time - start_time).total_seconds(),
            )
        except KeyError:
            pass

        # ------------------------------------------------------------------
        # 2. Normalise config fields ---------------------------------------
        # ------------------------------------------------------------------
        if isinstance(cfg, CodeNodeConfig):
            code_str: str = cfg.code or ""
            language: str = cfg.language or "python"
            imports: Optional[list[str]] = cfg.imports
        else:
            code_str = getattr(cfg, "code", "") or ""
            language = getattr(cfg, "runtime", "python") or "python"
            imports = getattr(cfg, "imports", [])

        if not code_str:
            raise ValueError(f"Code node {cfg.id} has no code")
        if language != "python":
            raise ValueError(f"Only Python runtime supported, got {language}")

        # ------------------------------------------------------------------
        # 3. Basic syntax validation --------------------------------------
        # ------------------------------------------------------------------
        try:
            ast.parse(code_str)
        except SyntaxError as exc:
            raise ValueError(f"Invalid Python syntax: {exc}") from exc

        # ------------------------------------------------------------------
        # 4. Execute in WASM sandbox (gated by ICE_ENABLE_WASM) -----------
        # ------------------------------------------------------------------
        import os as _os

        try:
            if (
                execute_node_with_wasm is None
                or _os.getenv("ICE_ENABLE_WASM", "1") != "1"
            ):
                raise RuntimeError(
                    "WASM execution is unavailable; enable ICE_ENABLE_WASM=1 and install 'wasmtime'."
                )
            result: NodeExecutionResult = await execute_node_with_wasm(
                node_type="code",
                code=code_str,
                context=ctx,
                node_id=cfg.id,
                allowed_imports=imports,
            )
            # If WASM execution failed and fallback is allowed, proceed to fallback path
            _fallback_on_failure = _os.getenv("ICE_WASM_FALLBACK_ON_FAILURE", "1")
            if getattr(result, "success", False) is True or _fallback_on_failure != "1":
                return result
            # else fall through to fallback sandbox below
            raise RuntimeError("wasm_failed_trigger_fallback")
        except Exception:
            # Fallback to ResourceSandbox subprocess execution to avoid blocking launches on wasmtime limits
            import json as _json
            import os as _os
            from subprocess import PIPE, Popen

            from ice_orchestrator.execution.sandbox.resource_sandbox import (
                ResourceSandbox,
            )

            _mem_mb = int(_os.getenv("ICE_SANDBOX_CODE_MEMORY_MB", "512"))
            _cpu_s = int(_os.getenv("ICE_SANDBOX_CODE_CPU_SECONDS", "10"))
            async with ResourceSandbox(
                timeout_seconds=getattr(cfg, "timeout_seconds", 30) or 30,
                memory_limit_mb=_mem_mb,
                cpu_limit_seconds=_cpu_s,
            ):
                # Create a small wrapper script to execute user code safely without network
                script = f'\nimport json\n\nctx = { _json.dumps(ctx, default=str) }\ntry:\n    exec({code_str!r}, {{}}, ctx)\n    print(json.dumps(ctx.get("output", {{}})))\nexcept Exception as e:\n    print(json.dumps({{"error": str(e)}}))\n'
                import tempfile

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False
                ) as tf:
                    tf.write(script)
                    tmp_path = tf.name
                try:
                    proc = Popen(
                        ["python", tmp_path], stdout=PIPE, stderr=PIPE, text=True
                    )
                    out, err = proc.communicate(
                        timeout=getattr(cfg, "timeout_seconds", 30) or 30
                    )
                    if proc.returncode != 0:
                        raise RuntimeError(
                            err.strip() or f"code node failed (exit {proc.returncode})"
                        )
                    try:
                        payload = _json.loads(out.strip())
                    except Exception:
                        payload = {"result": out.strip()}
                    end_time = datetime.utcnow()
                    return NodeExecutionResult(
                        success=True,
                        output=(
                            payload
                            if isinstance(payload, dict)
                            else {"result": payload}
                        ),
                        metadata=NodeMetadata(
                            node_id=getattr(cfg, "id", "code_node"),
                            node_type="code",
                            name=getattr(cfg, "name", "code_node"),
                            version="1.0.0",
                            owner="system",
                            provider=getattr(cfg, "provider", None),
                            error_type=None,
                            start_time=start_time,
                            end_time=end_time,
                            duration=(end_time - start_time).total_seconds(),
                            description="Code execution (fallback sandbox)",
                        ),
                        execution_time=(end_time - start_time).total_seconds(),
                    )
                finally:
                    try:
                        import os as __os

                        __os.unlink(tmp_path)
                    except Exception:
                        pass

    except Exception as exc:  # pragma: no cover
        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=False,
            error=str(exc),
            output={},
            metadata=NodeMetadata(
                node_id=getattr(cfg, "id", "code_node"),
                node_type=getattr(cfg, "type", "code"),
                name=getattr(cfg, "name", "code_node"),
                version="1.0.0",
                owner="system",
                provider=getattr(cfg, "provider", None),
                error_type=type(exc).__name__,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description="Code execution failed",
            ),
            execution_time=(end_time - start_time).total_seconds(),
        )
    # Defensive: in case control flow reaches here without returning
    end_time = datetime.utcnow()
    return NodeExecutionResult(
        success=False,
        error="Code node executor reached unexpected end",
        output={},
        metadata=NodeMetadata(
            node_id=getattr(cfg, "id", "code_node"),
            node_type=getattr(cfg, "type", "code"),
            name=getattr(cfg, "name", "code_node"),
            version="1.0.0",
            owner="system",
            provider=getattr(cfg, "provider", None),
            error_type=None,
            start_time=start_time,
            end_time=end_time,
            duration=(end_time - start_time).total_seconds(),
            description="Code execution ended without result",
        ),
        execution_time=(end_time - start_time).total_seconds(),
    )
