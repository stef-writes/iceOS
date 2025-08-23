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


@register_node("code")
async def code_node_executor(  # noqa: D401
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
