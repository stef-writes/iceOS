from datetime import datetime
from typing import Any, Dict, Optional

from ice_sdk.models.node_models import NodeExecutionResult, NodeMetadata
from ice_sdk import ToolService
from ice_sdk.base_node import BaseNode


class ToolNode(BaseNode):
    """Node implementation that delegates execution to a registered ToolService tool.

    Unlike :class:`ice_orchestrator.nodes.ai.ai_node.AiNode`, this node does *not* require any
    model-specific fields.  It simply takes the resolved context, merges it with
    any ``tool_args`` provided in the configuration, and invokes the
    ``ToolService``.
    """

    def __init__(
        self,
        config,
        context_manager=None,
        tool_service: Optional[ToolService] = None,
        *args,
        **kwargs,
    ):
        super().__init__(config)
        self.context_manager = context_manager
        self.tool_service = tool_service or ToolService()

    async def execute(self, context: Dict[str, Any]) -> NodeExecutionResult:  # type: ignore[override]
        start_time = datetime.utcnow()

        tool_name: Optional[str] = getattr(self.config, "tool_name", None)
        # Start with arguments provided in the node configuration.
        tool_args: Dict[str, Any] = dict(getattr(self.config, "tool_args", {}) or {})
        # Merge/override with the context coming from dependencies or chain.
        tool_args.update(context or {})

        if not tool_name:
            return NodeExecutionResult(
                success=False,
                error="No tool_name specified in node configuration.",
                metadata=NodeMetadata(
                    node_id=self.config.id,
                    node_type=self.config.type,
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    duration=0.0,
                    error_type="ConfigError",
                ),
            )

        # Execute the tool via ToolService.
        res = await self.tool_service.execute(tool_name, tool_args)

        metadata = NodeMetadata(
            node_id=self.config.id,
            node_type=self.config.type,
            start_time=start_time,
            end_time=datetime.utcnow(),
            duration=(datetime.utcnow() - start_time).total_seconds(),
            error_type=None if res["success"] else "ToolExecutionError",
        )

        return NodeExecutionResult(
            success=res["success"],
            error=res["error"],
            output=res["output"],
            metadata=metadata,
            execution_time=res["execution_time"],
        )

    # ------------------------------------------------------------------
    # Delegation helpers -------------------------------------------------
    # ------------------------------------------------------------------
    def __getattr__(self, name: str):
        """Delegate unknown attribute access to the underlying config.

        This makes ``ToolNode`` behave consistently with ``AiNode`` so that
        orchestration code can access fields such as ``input_mappings`` or
        ``dependencies`` directly on the node instance.
        """

        if hasattr(self.config, name):
            return getattr(self.config, name)
        raise AttributeError(f"'ToolNode' object has no attribute '{name}'")
