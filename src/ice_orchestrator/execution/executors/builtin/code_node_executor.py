"""Executor for code nodes."""

import ast
from datetime import datetime
from typing import Any, Dict, Optional

from ice_core.models import CodeNodeConfig, NodeExecutionResult
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry
from ice_orchestrator.execution.wasm_executor import execute_node_with_wasm

__all__ = ["code_node_executor"]


@register_node("code")
async def code_node_executor(  # noqa: D401, ANN001
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: Any,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:
    """Execute arbitrary Python code in the shared WASM sandbox."""
    start_time = datetime.utcnow()

    try:
        # ------------------------------------------------------------------
        # 1. Delegate to factory if registered -----------------------------
        # ------------------------------------------------------------------
        try:
            code_impl = registry.get_code_instance(getattr(cfg, "name", None) or cfg.id)
            out = await code_impl.execute(workflow=workflow, cfg=cfg, ctx=ctx)
            if isinstance(out, NodeExecutionResult):
                return out
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
            code_str: str = cfg.code
            language: str = cfg.language
            imports: Optional[list[str]] = cfg.imports
        else:
            code_str = getattr(cfg, "code", "")
            language = getattr(cfg, "runtime", "python")
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
        # 4. Execute in WASM sandbox --------------------------------------
        # ------------------------------------------------------------------
        result: NodeExecutionResult = await execute_node_with_wasm(
            node_type="code",
            code=code_str,
            context=ctx,
            node_id=cfg.id,
            allowed_imports=imports,
        )
        return result

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
                description=f"Code execution failed: {language}",
            ),
            execution_time=(end_time - start_time).total_seconds(),
        )
