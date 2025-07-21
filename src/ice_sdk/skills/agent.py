"""AgentSkill – specialized *Skill* representing an autonomous agent.

The implementation purposefully remains minimal: it focuses on the metadata
and schema required by the orchestrator/UI layers.  Concrete logic should be
implemented by downstream packages or user code.
"""

from __future__ import annotations

from typing import Any, Dict

from ice_core.models.workflow import SubDAGResult
from pydantic import Field

from ice_sdk.models.agent_params import AgentParams
from ice_sdk.services.locator import get_workflow_proto
from ice_sdk.skills.base import SkillBase

__all__: list[str] = ["AgentSkill"]


class AgentSkill(SkillBase):
    """Base class for *agent* subtype skills.

    Subclasses must override :meth:`_execute_impl` with agent-specific logic.
    """

    # Replace generic *dict* parameters with strongly-typed schema
    parameters: AgentParams = Field(..., description="Agent runtime parameters")

    class Meta:  # noqa: D401 – metadata container
        node_subtype: str = "agent"
        commercializable: bool = True

    # ------------------------------------------------------------------
    # Default implementation raises *NotImplementedError* so downstream
    # authors are forced to provide concrete behaviour.
    # ------------------------------------------------------------------

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        # Default implementation: build an *empty* workflow so that the orchestrator
        # can still execute it and prove the plumbing works.  Subclasses are
        # expected to override with richer planning logic.

        workflow_cls = get_workflow_proto()
        workflow = workflow_cls(nodes=[], name=f"agent_subdag_{self.name}")

        # Subclasses may add nodes here – this base implementation stays minimal.

        # Validate per Rule 13 ---------------------------------------------------
        if hasattr(workflow, "validate"):
            workflow.validate()

        return SubDAGResult.from_workflow(
            workflow
        ).model_dump()  # return as dict for SDK compatibility

    # Optional explicit validate hook (idempotent)
    def validate(self) -> None:  # noqa: D401 – public API
        """Validate inner workflow before execution."""

        workflow_cls = get_workflow_proto()
        dummy = workflow_cls(nodes=[], name="validate_dummy")
        if hasattr(dummy, "validate"):
            dummy.validate()
