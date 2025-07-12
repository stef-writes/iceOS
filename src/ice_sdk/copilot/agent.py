"""ICE Copilot – Socratic design assistant (core agent implementation).

This module was moved into *ice_sdk.copilot.core* so the public package
``ice_sdk.copilot`` can stay slim while internals live one level deeper.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from ice_sdk.agents.flow_design_agent import (
    _DummyResponse,  # type: ignore[attr-defined]
)
from ice_sdk.agents.flow_design_agent import _DummySession  # type: ignore[attr-defined]
from ice_sdk.agents.flow_design_agent import FlowDesignAgent, TestContextStore
from ice_sdk.chain_builder.engine import ChainDraft

from .session import WorkflowSession

__all__: list[str] = ["IceCopilot"]


class IceCopilot(FlowDesignAgent):  # type: ignore[misc]  # noqa: D401 – FlowDesignAgent dynamic
    """Guides a Q&A flow to elicit workflow requirements from the user."""

    _QUESTION_FLOW: List[Tuple[str, str]] = [
        ("What's the primary goal of this workflow?", "core_objective"),
        (
            "Which external systems (APIs, SaaS) should we integrate?",
            "external_dependencies",
        ),
        ("Are data transformations required between steps?", "data_pipelines"),
        ("Should parts of the workflow run in parallel?", "concurrency_needs"),
        ("How should errors be handled?", "error_policy"),
    ]

    def __init__(self, context: TestContextStore | None = None):  # noqa: D401
        self.context = context or TestContextStore()
        super().__init__(self.context)
        self._session_cache: Dict[int, WorkflowSession] = {}

    # ------------------------------------------------------------------ helpers
    @property
    def question_flow(self) -> List[str]:  # noqa: D401
        return [q for q, _ in self._QUESTION_FLOW]

    # ------------------------------------------------------------------ dialogue
    def generate_response(self, session: _DummySession) -> _DummyResponse:  # type: ignore[override]
        sid = id(session)
        state = self._session_cache.setdefault(sid, WorkflowSession())

        # Capture latest user msg if new -----------------------------------
        user_msgs = [msg for role, msg in session._messages if role == "user"]
        if len(user_msgs) > len(state.answers):
            idx = len(state.answers)
            if idx < len(self._QUESTION_FLOW):
                _, key = self._QUESTION_FLOW[idx]
                state.answers[key] = user_msgs[-1]

        answered = len(state.answers)
        if answered < len(self._QUESTION_FLOW):
            prompt, _ = self._QUESTION_FLOW[answered]
            rsp = _DummyResponse(prompt)
            rsp.requires_input = True
            return rsp

        summary = "\n".join(
            f"• {k.replace('_', ' ').title()}: {v}" for k, v in state.answers.items()
        )
        return _DummyResponse(
            "Great! Here's a summary of your workflow needs:\n" + summary,
        )

    # ------------------------------------------------------------------ spec gen
    async def generate_agent_spec(
        self, goal: str
    ) -> Dict[str, object]:  # noqa: D401, ANN401
        """Return a minimal AgentConfig YAML-ready payload (placeholder)."""
        return {
            "name": goal.replace(" ", "_").lower(),
            "instructions": goal,
            "model": "gpt-4o",
            "tools": [],
        }

    async def generate_chain_draft(self, brief: str) -> ChainDraft:  # noqa: D401
        """Return a quick heuristic ChainDraft based on *brief*.

        An LLM-backed version will replace this, but for now we detect the
        presence of words like "api" / "database" to choose a ToolNode vs
        AiNode scaffold.
        """
        from ice_sdk.chain_builder.engine import BuilderEngine

        draft = BuilderEngine.start(total_nodes=1, chain_name="auto_chain")
        draft.persist_interm_outputs = False

        node_type = "tool" if "api" in brief.lower() else "ai"
        draft.nodes.append(
            {
                "type": node_type,
                "name": "auto_node",
                "model": "gpt-4o" if node_type == "ai" else None,
                "dependencies": [],
            }
        )
        return draft
