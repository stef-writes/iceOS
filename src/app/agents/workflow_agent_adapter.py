from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from app.chains.orchestration.level_based_script_chain import LevelBasedScriptChain
from app.models.node_models import (
    ChainExecutionResult,
    NodeExecutionResult,
    NodeMetadata,
)
from app.utils.context.session_state import SessionState


class WorkflowAgentAdapter:
    """Wrap a :class:`LevelBasedScriptChain` so it behaves like an agent.

    This lets the `RouterAgent` (or any other caller) treat an entire workflow
    as a single black-box agent.
    """

    def __init__(
        self,
        chain: LevelBasedScriptChain,
        *,
        name: Optional[str] = None,
        description: str | None = None,
    ) -> None:
        self.chain = chain
        self._name = name or getattr(chain, "name", "workflow_agent")
        self._description = description or "Workflow composed of multiple nodes"

    # ------------------------------------------------------------------
    @property
    def name(self) -> str:  # noqa: D401
        return self._name

    @property
    def description(self) -> str:  # noqa: D401
        return self._description

    # ------------------------------------------------------------------
    async def execute(
        self,
        session: SessionState | None,
        input_context: Dict[str, Any] | None = None,
        **kwargs,
    ) -> NodeExecutionResult:  # noqa: D401
        # Inject *input_context* into chain's initial context so first-level
        # nodes can access it.
        if input_context:
            if (
                hasattr(self.chain, "initial_context")
                and self.chain.initial_context is not None
            ):
                self.chain.initial_context.update(input_context)
            else:
                self.chain.initial_context = dict(input_context)

        start = datetime.utcnow()
        chain_result: ChainExecutionResult = await self.chain.execute()

        # Persist to session if provided
        if session is not None and chain_result.output is not None:
            session.set_output(self.name, chain_result.output)

        return NodeExecutionResult(
            success=chain_result.success,
            error=chain_result.error,
            output=chain_result.output,
            metadata=NodeMetadata(
                node_id=self._name,
                node_type="workflow_agent",
                start_time=start,
                end_time=datetime.utcnow(),
                duration=None,
                provider=None,
            ),
            execution_time=chain_result.execution_time,
            token_stats=chain_result.token_stats,
        )
