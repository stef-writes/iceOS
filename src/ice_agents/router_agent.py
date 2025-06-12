from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional

from ice_agents.registry import AgentRegistry
from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.models.node_models import NodeExecutionResult, NodeMetadata
from ice_orchestrator.services.llm_service import LLMService
from ice_sdk.context.session_state import SessionState


class RouterAgent:
    """An agent that selects *one* registered sub-agent via an LLM call.

    Prompt design is minimal for now – it enumerates available agents and asks
    the model to answer with **just** the chosen agent `name` (verbatim).  Any
    additional text is ignored via regex.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        llm_config: Optional[LLMConfig] = None,
        name: str = "router_agent",
        description: str | None = None,
    ) -> None:
        self.registry = registry
        self.llm_config = llm_config or LLMConfig(
            provider=ModelProvider.OPENAI, model="gpt-3.5-turbo"
        )
        self.name = name
        self.description = description or "Routes user input to the best sub-agent"
        self.llm_service = LLMService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def execute(
        self, session: SessionState, user_input: Dict[str, Any] | None = None
    ) -> NodeExecutionResult:  # noqa: D401
        user_input = user_input or {}
        text = user_input.get("text") or user_input.get("query") or str(user_input)

        prompt = self._build_prompt(text)
        start = datetime.utcnow()
        llm_response, usage, err = await self.llm_service.generate(
            self.llm_config, prompt=prompt, context={}
        )
        if err:
            # Fallback: pick first registered agent to keep flow running.
            fallback_agent = next(iter(self.registry))
            agent_result = await fallback_agent.execute(session, user_input)
            agent_result.metadata.error_type = (
                agent_result.metadata.error_type or "RouterLLMFallback"
            )
            agent_result.metadata.node_id = self.name
            return agent_result

        target_name = self._extract_agent_name(llm_response)
        if target_name not in self.registry:
            return NodeExecutionResult(
                success=False,
                error=f"Router selected unknown agent '{target_name}'",
                output=None,
                metadata=NodeMetadata(
                    node_id=self.name,
                    node_type="router",
                    start_time=start,
                    end_time=datetime.utcnow(),
                    duration=None,
                    error_type="RoutingError",
                    provider=self.llm_config.provider,
                ),
            )

        # Call target agent ---------------------------------------------
        target_agent = self.registry.get(target_name)
        agent_result = await target_agent.execute(session, user_input)

        # Optionally: persist routing decision in session
        session.agent_state.setdefault(self.name, {})["last_route"] = target_name

        return agent_result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _build_prompt(self, user_text: str) -> str:  # noqa: D401
        lines = [
            "You are a routing agent. Choose which specialised agent should handle the user's request.",
            "Respond with ONLY the agent name, nothing else.",
            "Available agents:",
        ]
        for agent in self.registry:
            lines.append(f"- {agent.name}: {agent.description or 'No description.'}")
        lines.append("")
        lines.append("User request:")
        lines.append(user_text)
        lines.append("\nYour answer (just the agent name):")
        return "\n".join(lines)

    @staticmethod
    def _extract_agent_name(raw: str) -> str:  # noqa: D401
        # Take first word on first line matching allowed chars
        m = re.search(r"([a-zA-Z0-9_\-]+)", raw)
        return m.group(1) if m else raw.strip().split()[0]
