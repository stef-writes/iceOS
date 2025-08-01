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

from ice_sdk.services.locator import ServiceLocator


class ToolService:  # pylint: disable=too-few-public-methods
    """Thin forwarding facade for tool execution.

    SDK / API code can depend on this class for type-checking.  The real
    logic lives in :pyclass:`ice_orchestrator.services.tool_execution_service.ToolExecutionService`.
    """

    _delegate_key: str = "tool_execution_service"

    # ---------------------------------------------------------------------
    # Convenience getters --------------------------------------------------
    # ---------------------------------------------------------------------
    @property
    def _delegate(self) -> Any:  # type: ignore[return-annotation]
        delegate = ServiceLocator.get(self._delegate_key)
        if delegate is None:
            raise RuntimeError(
                "ToolExecutionService is not registered – orchestrator not initialised?"
            )
        return delegate

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
        return await self._delegate.execute_tool(tool_name, inputs, context)  # type: ignore[arg-type, no-any-return]

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """Return metadata for all registered tools."""
        return self._delegate.list_tools()  # type: ignore[no-any-return]

    # Expose attributes of delegate transparently (optional)
    def __getattr__(self, item: str) -> Any:  # noqa: D401
        return getattr(self._delegate, item)
