"""Internal proxy for WorkflowBuilder.map sugar."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ice_builder.dsl.workflow import WorkflowBuilder


class _MapBuilderProxy:  # noqa: D401 – internal helper
    def __init__(self, builder: "WorkflowBuilder", items_source: str) -> None:
        self._b = builder
        self._src = items_source

    def with_tool(
        self, node_id: str, *, tool_name: str, **tool_args: Any
    ) -> "WorkflowBuilder":  # noqa: D401
        """Add tool and loop wrapper automatically."""
        loop_id = f"{node_id}_loop"
        # Body tool first so loop can reference it
        self._b.add_tool(node_id, tool_name=tool_name, **tool_args)
        # Find the recently added tool config to embed in the loop body
        from typing import Union

        from ice_core.models import NodeConfig
        from ice_core.models.node_models import HumanNodeConfig, MonitorNodeConfig

        ExtendedNodeConfig = Union[NodeConfig, HumanNodeConfig, MonitorNodeConfig]

        body_cfg: ExtendedNodeConfig | None = next(
            (n for n in self._b.nodes if getattr(n, "id", None) == node_id),
            None,
        )
        if body_cfg is None:
            raise ValueError(
                f"Tool node {node_id} not found on builder when constructing loop body"
            )

        # Only NodeConfig is allowed in loop body per type hints; if the last node
        # is an extended type, raise for clarity rather than widening types here.
        if not hasattr(body_cfg, "type"):
            raise TypeError("Unexpected node type for loop body")

        self._b.add_loop(
            loop_id,
            items_source=self._src,
            body=[body_cfg],  # type: ignore[list-item]
            item_var="item",
        )
        self._b.connect(loop_id, node_id)
        return self._b
