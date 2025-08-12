"""Tool execution service for the orchestrator runtime."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from ice_api.services.component_repo import choose_component_repo
from ice_api.services.component_service import ComponentService
from ice_core.metrics import EXEC_COMPLETED, EXEC_STARTED
from ice_core.models import NodeType
from ice_core.protocols.node import INode
from ice_core.unified_registry import registry


class ToolExecutionService:
    """Handles tool execution within the orchestrator runtime."""

    async def execute_tool(
        self, tool_name: str, inputs: Dict[str, Any], context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute a tool by name with given inputs.

        Args:
            tool_name: Name of the tool to execute
            inputs: Input parameters for the tool
            context: Optional execution context

        Returns:
            Tool execution results

        Raises:
            ValueError: If tool not found
            Exception: If tool execution fails
        """
        # Get tool instance from registry
        tool_instance = self._get_tool_instance(tool_name)

        if tool_instance is None:
            from ice_core.exceptions import ToolFactoryResolutionError

            raise ToolFactoryResolutionError(tool_name, "not found in registry")

        # Execute the tool (inject execution context when supported)
        execute_fn = getattr(tool_instance, "execute", None)
        if execute_fn is None:
            from ice_core.exceptions import ToolFactoryResolutionError

            raise ToolFactoryResolutionError(tool_name, "missing execute() method")

        EXEC_STARTED.inc()
        # Handle both sync and async execution
        # Try to pass context/memory via conventional kw if accepted
        try:
            from inspect import signature

            sig = signature(execute_fn)
            if "context" in sig.parameters and context is not None:
                inputs = {**inputs, "context": context}
            if (
                "memory" in sig.parameters
                and context is not None
                and isinstance(context, dict)
            ):
                mem = context.get("memory")
                if mem is not None:
                    inputs = {**inputs, "memory": mem}
        except Exception:
            pass

        if asyncio.iscoroutinefunction(execute_fn):
            result = await execute_fn(**inputs)
        else:
            # Run sync function in thread pool
            result = await asyncio.to_thread(execute_fn, **inputs)

        EXEC_COMPLETED.inc()
        if result is None:
            result = {}
        if not isinstance(result, dict):
            try:
                result = dict(result)  # type: ignore[arg-type]
            except Exception:
                result = {"result": result}
        # Ensure str keys
        coerced: Dict[str, Any] = {str(k): v for k, v in result.items()}
        return coerced

    def _get_tool_instance(self, tool_name: str) -> Optional[INode]:
        """Get tool instance from unified registry.

        Tries, in order:
        1) Public factory API (register_tool_factory → get_tool_instance)
        2) Pre-instantiated instances map
        3) Class registry with direct instantiation
        """
        # 1) Preferred: public factory resolution
        try:
            from ice_core.unified_registry import get_tool_instance as _get_via_factory

            return _get_via_factory(tool_name)  # type: ignore[return-value]
        except Exception:
            pass

        # 2) Legacy: pre-instantiated instance lookup
        tool_instance = registry._instances.get(NodeType.TOOL, {}).get(tool_name)  # type: ignore[no-any-return]
        if tool_instance:
            return tool_instance

        # 3) Legacy: class registry
        tool_class = registry._nodes.get(NodeType.TOOL, {}).get(tool_name)  # type: ignore[attr-defined]
        if tool_class:
            try:
                return tool_class()  # type: ignore[no-any-return]
            except Exception:
                return None

        # 4) Repository-backed sandbox fallback
        try:
            # Access the component repository via API-layer helper
            # Note: choose_component_repo accepts app or request context; for runtime
            # fallback we pass a minimal stub with .app/state attributes if needed.
            repo = choose_component_repo(
                type(
                    "_Stub",
                    (),
                    {"app": type("_A", (), {"state": type("_S", (), {})()})()},
                )()
            )
            service = ComponentService(repo)
            import asyncio

            data, _ = asyncio.get_event_loop().run_until_complete(
                service.get("tool", tool_name)
            )  # type: ignore[arg-type]
            if not data or not isinstance(data, dict):
                return None
            definition = data.get("definition", {})
            tool_class_code = definition.get("tool_class_code")
            tool_factory_code = definition.get("tool_factory_code")
            input_schema = definition.get("tool_input_schema")
            output_schema = definition.get("tool_output_schema")

            if not (tool_class_code or tool_factory_code):
                return None

            # Build a minimal sandboxed adapter that exposes execute(**inputs)
            class _RepoToolAdapter:  # pylint: disable=too-few-public-methods
                name = tool_name
                description = f"Repository-backed tool: {tool_name}"

                async def execute(self, **inputs: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
                    # Validate input against schema when provided (best-effort)
                    if input_schema and isinstance(inputs, dict):
                        try:
                            from ice_core.utils.json_schema import validate_with_schema

                            ok, errs, _ = validate_with_schema(inputs, input_schema)
                            if not ok:
                                raise ValueError(
                                    "Input schema validation failed: " + "; ".join(errs)
                                )
                        except Exception:
                            pass

                    # Execute code via WASM sandbox executor path (Python)
                    try:
                        from ice_orchestrator.execution.wasm_executor import (
                            execute_node_with_wasm,
                        )

                        # Choose code to run: prefer factory calling pattern that returns dict
                        code_snippets = []
                        if tool_class_code:
                            code_snippets.append(tool_class_code)
                        if tool_factory_code:
                            code_snippets.append(tool_factory_code)
                        code = (
                            "\n\n".join(code_snippets)
                            + "\n\n"
                            + (
                                "result = await create_{}(**inputs) if 'create_{}' in globals() else None\n".format(
                                    tool_name, tool_name
                                )
                                + "if result and hasattr(result, 'run'):\n    result = await result.run(**inputs) if hasattr(result.run, '__call__') else result\n"
                                + "output.update(result if isinstance(result, dict) else {'result': result})\n"
                            )
                        )

                        res = await execute_node_with_wasm(
                            node_type="tool",
                            code="",  # code delivered via context for subprocess path
                            context={"__code": code, **inputs},
                            node_id=f"tool:{tool_name}",
                            allowed_imports=[
                                "json",
                                "math",
                                "re",
                                "datetime",
                                "hashlib",
                                "base64",
                                "uuid",
                            ],
                        )
                        out = res.output if hasattr(res, "output") else {}
                    except Exception as exc:
                        raise RuntimeError(
                            f"Sandboxed tool execution failed: {exc}"
                        ) from exc

                    # Validate output
                    if output_schema and isinstance(out, dict):
                        try:
                            from ice_core.utils.json_schema import validate_with_schema

                            ok, errs, _ = validate_with_schema(out, output_schema)
                            if not ok:
                                raise ValueError(
                                    "Output schema validation failed: "
                                    + "; ".join(errs)
                                )
                        except Exception:
                            pass
                    # Ensure repository adapter returns mapping
                    if not isinstance(out, dict):
                        try:
                            out = dict(out)  # type: ignore[arg-type]
                        except Exception:
                            out = {"result": out}
                    return {str(k): v for k, v in out.items()}

            return _RepoToolAdapter()  # type: ignore[return-value]
        except Exception:
            return None

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all available tools with their metadata.

        Returns:
            dict[str, dict[str, Any]]: Mapping of tool names to metadata dictionaries.
        """
        tools: Dict[str, Dict[str, Any]] = {}

        # Get all registered tools from unified registry
        # Collect both pre-instantiated and class-only tools
        tool_registry: Dict[str, Any] = {}
        # Instances already registered
        tool_registry.update(registry._instances.get(NodeType.TOOL, {}))  # type: ignore[attr-defined]
        # Classes that are registered but not yet instantiated
        tool_registry.update(registry._nodes.get(NodeType.TOOL, {}))  # type: ignore[attr-defined]

        for tool_name, tool_class in tool_registry.items():
            try:
                # Build tool metadata
                tools[tool_name] = {
                    "name": tool_name,
                    "description": tool_class.__doc__ or "No description",
                    "category": getattr(tool_class, "category", "general"),
                }
            except Exception:  # pragma: no cover – defensive
                # Skip tools that can't be introspected for whatever reason
                continue

        return tools

    # ------------------------------------------------------------------
    # Convenience helpers ----------------------------------------------
    # ------------------------------------------------------------------
    def available_tools(self) -> list[str]:  # noqa: D401 – simple name list helper
        """Return a list of all available tool names.

        This is a lightweight helper primarily for HTTP discovery endpoints that
        only need the names rather than full metadata.

        Returns:
            list[str]: All registered tool names.
        """
        return list(self.list_tools().keys())
