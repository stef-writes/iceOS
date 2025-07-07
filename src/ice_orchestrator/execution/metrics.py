from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from pydantic import BaseModel, Field

# NOTE: To avoid a heavy import chain, we import NodeExecutionResult lazily in update()
# to keep this utility lightweight and free from orchestrator dependencies at import time.

if TYPE_CHECKING:
    from ice_sdk.models.node_models import NodeExecutionResult


class ChainMetrics(BaseModel):
    """Metrics for ScriptChain execution (tokens, cost, per-node usage)."""

    total_tokens: int = 0
    total_cost: float = 0.0
    node_metrics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    def update(self, node_id: str, result: "NodeExecutionResult") -> None:  # noqa: F821
        """Merge *result.usage* stats into cumulative metrics.

        The method is intentionally tolerant: when *result.usage* is missing or
        incomplete the update becomes a no-op instead of raising, protecting the
        orchestrator from partial provider implementations.
        """

        usage = getattr(result, "usage", None)
        if not usage:
            return

        self.total_tokens += getattr(usage, "total_tokens", 0)
        # Support both historical *cost* and new *total_cost* field names.
        self.total_cost += getattr(usage, "total_cost", getattr(usage, "cost", 0.0))
        try:
            self.node_metrics[node_id] = usage.model_dump()  # type: ignore[attr-defined]
        except Exception:
            # Fallback to dict() in case provider returns a plain object.
            self.node_metrics[node_id] = dict(usage) if isinstance(usage, dict) else {}

    def as_dict(self) -> Dict[str, Any]:
        """Return a plain-dict representation suitable for JSON serialization."""

        return {
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "node_metrics": self.node_metrics,
        }
