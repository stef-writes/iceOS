"""SDK-facing proxy for the runtime ToolExecutionService.

This class lives in the SDK layer so that SDK utilities and external
API layers can reference a stable `ToolService` type **without**
importing the orchestrator package directly (maintains layer
boundaries).

At runtime the real implementation is provided by the orchestrator and
registered in the `ServiceLocator` under the key ``tool_execution_service``.
The proxy simply forwards every call to that registered instance.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ice_core.protocols.runtime_factories import ToolExecutionServiceProtocol
from ice_core.runtime import tool_execution_service


class ToolService:  # pylint: disable=too-few-public-methods
    """Thin forwarding facade for tool execution.

    SDK / API code can depend on this class for type-checking.  The real
    logic lives in :pyclass:`ice_orchestrator.services.tool_execution_service.ToolExecutionService`.
    """

    _delegate_instance: ToolExecutionServiceProtocol | None = None

    # ---------------------------------------------------------------------
    # Convenience getters --------------------------------------------------
    # ---------------------------------------------------------------------
    @property
    def _delegate(self) -> ToolExecutionServiceProtocol:
        if self._delegate_instance is None:
            if tool_execution_service is None:
                raise RuntimeError(
                    "`tool_execution_service` not set. The orchestrator layer must assign "
                    "ice_core.runtime.tool_execution_service at start-up."
                )
            self._delegate_instance = tool_execution_service
        return self._delegate_instance

    # ------------------------------------------------------------------
    # Public API mirrors the real service --------------------------------
    # ------------------------------------------------------------------
    async def execute_tool(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        context: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Forward to runtime service."""
        return await self._delegate.execute_tool(tool_name, inputs, context)

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """Return metadata for all registered tools."""
        return self._delegate.list_tools()

    def available_tools(self) -> list[str]:  # noqa: D401 – helper alias
        """Return a flat list of available tool names.

        This delegates to :pyfunc:`list_tools` and extracts the keys for
        convenience.  It exists mainly for backwards compatibility with older
        API routes that returned just the names.
        """
        return list(self.list_tools().keys())

    # Expose attributes of delegate transparently (optional)
    def __getattr__(self, item: str) -> Any:  # noqa: D401
        return getattr(self._delegate, item)
