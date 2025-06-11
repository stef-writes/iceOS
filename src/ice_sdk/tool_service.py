from __future__ import annotations

import asyncio
import traceback
from typing import Any, Dict

import structlog
from pydantic import ValidationError

from ice_sdk import BaseTool, iter_tool_classes

logger = structlog.get_logger(__name__)


class ToolExecutionError(Exception):
    """Raised when a tool fails to execute successfully."""


class ToolService:  # noqa: D401
    """Async service for tool discovery and invocation.

    The service drives discovery via the *ice_sdk* plugin registry and provides
    uniform async execution, validation and error handling.  It acts as a
    single façade for the rest of the runtime.
    """

    def __init__(self, timeout: float = 10.0):
        self.registry: Dict[str, BaseTool] = {}
        self.timeout = timeout

        # Automatically register all available tool classes.
        for tool_cls in iter_tool_classes():
            try:
                self.register_tool(tool_cls())
            except Exception as exc:  # noqa: BLE001 – broad except intentional
                logger.error(
                    "Failed to register tool", tool_cls=str(tool_cls), error=str(exc)
                )

    # ------------------------------------------------------------------
    # Registry management ------------------------------------------------
    # ------------------------------------------------------------------
    def register_tool(self, tool: BaseTool):  # noqa: D401
        self.registry[tool.name] = tool
        logger.debug("Registered tool", name=tool.name)

    def list_tools_with_schemas(self) -> list[dict[str, Any]]:  # noqa: D401
        tools = []
        for tool in self.registry.values():
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters_schema": tool.get_parameters_json_schema(),
                    "output_schema": tool.get_output_json_schema(),
                    "usage_example": getattr(tool, "usage_example", None),
                }
            )
        return tools

    # ------------------------------------------------------------------
    # Execution ----------------------------------------------------------
    # ------------------------------------------------------------------
    async def execute(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:  # noqa: D401
        if tool_name not in self.registry:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found.",
                "output": None,
                "tool_name": tool_name,
                "execution_time": 0.0,
            }

        tool = self.registry[tool_name]
        loop = asyncio.get_event_loop()
        start = loop.time()

        try:
            # Validate parameters using the tool's Pydantic schema
            validated_params = tool.parameters_schema(**parameters)

            if asyncio.iscoroutinefunction(tool.run):
                coro = tool.run(**validated_params.model_dump())
            else:
                coro = loop.run_in_executor(
                    None, tool.run, **validated_params.model_dump()
                )

            result = await asyncio.wait_for(coro, timeout=self.timeout)
            success, error = True, None
        except ValidationError as ve:
            logger.error("Parameter validation failed", tool=tool_name, error=str(ve))
            result, success, error = None, False, f"Parameter validation failed: {ve}"
        except Exception as exc:  # noqa: BLE001 – broad except required
            logger.error("Tool execution failed", tool=tool_name, error=str(exc))
            logger.debug(traceback.format_exc())
            result, success, error = None, False, f"Tool '{tool_name}' failed: {exc}"

        end = loop.time()
        return {
            "success": success,
            "output": result,
            "error": error,
            "tool_name": tool_name,
            "execution_time": end - start,
        }
