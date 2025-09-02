from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ice_api.dependencies import rate_limit
from ice_api.errors import PreviewSandboxError
from ice_api.security import require_auth


class PreviewToolRequest(BaseModel):
    """Request to preview-execute a generated code tool in a sandbox.

    Parameters
    ----------
    language : str
        Programming language ("python" or "javascript").
    code : str
        Inline code to execute.
    inputs : dict[str, Any]
        Runtime inputs passed to the code node.
    imports : list[str]
        Optional allowed imports for the sandbox.
    timeout_seconds : int | None
        Optional overall timeout for the execution (seconds).

    Example
    -------
    >>> PreviewToolRequest(language="python", code="print('hi')", inputs={})
    """

    language: str = Field(default="python")
    code: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    imports: List[str] = Field(default_factory=list)
    timeout_seconds: Optional[int] = Field(default=5, ge=1, le=30)


class PreviewToolResponse(BaseModel):
    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    logs: Optional[List[Dict[str, Any]]] = None


router = APIRouter(
    prefix="/api/v1/builder/preview",
    tags=["builder", "preview"],
    dependencies=[Depends(require_auth)],
)


@contextmanager
def _inline_code_enabled() -> Any:
    prev = os.getenv("ICE_ENABLE_INLINE_CODE")
    os.environ["ICE_ENABLE_INLINE_CODE"] = "1"
    try:
        yield
    finally:
        if prev is None:
            try:
                del os.environ["ICE_ENABLE_INLINE_CODE"]
            except Exception:
                pass
        else:
            os.environ["ICE_ENABLE_INLINE_CODE"] = prev


@router.post(
    "/tool", response_model=PreviewToolResponse, dependencies=[Depends(rate_limit)]
)
async def preview_tool(req: PreviewToolRequest) -> PreviewToolResponse:  # noqa: D401
    """Run generated code in a strict sandbox without registering it.

    Returns structured logs/results; never persists or registers components.
    """
    # Construct a minimal blueprint with a single code node
    from ice_core.models.mcp import Blueprint, NodeSpec

    # Enable inline code and force WASM-only execution for the lifetime of this preview
    with _inline_code_enabled():
        # Force WASM on and disable fallback so preview never escapes the sandbox
        os.environ["ICE_ENABLE_WASM"] = "1"
        os.environ["ICE_WASM_FALLBACK_ON_FAILURE"] = "0"
        try:
            # Pre-validate code with a strict AST import allowlist
            import ast as _ast

            allowed_imports = set(
                (req.imports or [])
                + [
                    "json",
                    "math",
                    "datetime",
                    "re",
                    "urllib.parse",
                    "base64",
                    "hashlib",
                    "uuid",
                    "random",
                    "string",
                    "time",
                    "collections",
                    "itertools",
                    "functools",
                    "operator",
                ]
            )
            try:
                tree = _ast.parse(req.code)
            except SyntaxError as e:
                raise PreviewSandboxError(f"Invalid code syntax: {e}")
            for node in _ast.walk(tree):
                if isinstance(node, _ast.Import):
                    for alias in node.names:
                        base = (alias.name or "").split(".")[0]
                        if base and base not in {
                            m.split(".")[0] for m in allowed_imports
                        }:
                            raise PreviewSandboxError(
                                f"Import '{base}' is not allowed in preview sandbox"
                            )
                elif isinstance(node, _ast.ImportFrom):
                    base = (node.module or "").split(".")[0]
                    if base and base not in {m.split(".")[0] for m in allowed_imports}:
                        raise PreviewSandboxError(
                            f"Import '{base}' is not allowed in preview sandbox"
                        )

            node: Dict[str, Any] = {
                "id": "n1",
                "type": "code",
                "dependencies": [],
                "language": req.language,
                "code": req.code,
                "sandbox": True,
                # Treat imports as a strict allowlist; default to empty
                "imports": req.imports or [],
            }
            bp = Blueprint(nodes=[NodeSpec.model_validate(node)])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid code node: {e}")

        # Execute using orchestrator workflow service with strict limits (inherited sandbox)
        try:
            from importlib import import_module

            WorkflowExecutionService = getattr(
                import_module("ice_orchestrator.services.workflow_execution_service"),
                "WorkflowExecutionService",
            )
            service = WorkflowExecutionService()
        except Exception as exc:
            raise HTTPException(
                status_code=503, detail=f"Orchestrator unavailable: {exc}"
            )

        try:
            # Execute single node blueprint via orchestrator service
            result = await service.execute_blueprint(
                node_specs=[
                    NodeSpec.model_validate(
                        {
                            "id": n.id,
                            "type": n.type,
                            **n.model_dump(exclude={"id", "type"}),
                        }
                    )
                    for n in bp.nodes
                ],
                inputs=req.inputs or {},
                name="builder_preview",
            )
        except Exception as exc:
            raise PreviewSandboxError(f"Sandbox execution failed: {exc}")

        # Normalize result
        try:
            success = bool(getattr(result, "success", True))
            output = getattr(result, "output", None)
            err = getattr(result, "error", None)
            logs: List[
                Dict[str, Any]
            ] = []  # placeholder; wire executor logs if available later
            return PreviewToolResponse(
                success=success, output=output, error=err, logs=logs
            )
        except Exception:
            # Fallback to raw repr
            return PreviewToolResponse(success=True, output=str(result))
