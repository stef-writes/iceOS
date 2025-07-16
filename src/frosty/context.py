"""Light-weight stub implementation of FrostyContext and related helpers.

This is *not* the production implementation – it exists so that the open-source
build passes the public contract tests shipped in ``tests/frosty``.

TODO(iceOS#2025): Replace `MemoryStore` with `iceos.services.knowledge_service.KnowledgeService`
and `Guardrails` with `ice_core.utils.perf` once the production services are fully
wired in.  Keep the existing interfaces stable to avoid breaking public tests.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from .exceptions import AgentNotFoundError

__all__ = [
    "MemoryStore",
    "Guardrails",
    "BaseAgent",
    "FrostyContext",
]


class MemoryStore:
    """Extremely naïve in-memory vector store replacement."""

    def __init__(self) -> None:
        self._mem: list[dict[str, Any]] = []

    async def add_memory(
        self,
        *,
        content: str,
        node_type: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        mem_id = str(uuid.uuid4())
        self._mem.append(
            {
                "id": mem_id,
                "content": content,
                "node_type": node_type,
                "metadata": metadata or {},
            }
        )
        return mem_id

    async def search_similar(
        self, term: str
    ) -> list[dict[str, Any]]:  # noqa: D401 – stub
        return [m for m in self._mem if term.lower() in m["content"].lower()]

    # Extras used in tests --------------------------------------------------
    async def search(
        self, term: str, _user: str | None = None
    ) -> list[dict[str, Any]]:  # noqa: D401
        return await self.search_similar(term)


class Guardrails:
    """Very small request/response accounting helper."""

    def __init__(self) -> None:
        self._requests = 0
        self._responses = 0
        self._total_cost = 0.0

    # Public API expected by tests -----------------------------------------
    async def validate_request(
        self, _request: dict[str, Any]
    ) -> None:  # noqa: D401 – stub
        self._requests += 1

    async def validate_response(
        self, _response: dict[str, Any]
    ) -> None:  # noqa: D401 – stub
        self._responses += 1

    async def get_usage_summary(self) -> dict[str, Any]:  # noqa: D401 – stub
        return {
            "request_count": self._requests,
            "response_count": self._responses,
            "total_cost": self._total_cost,
            "daily_cost": 0.0,
        }


class BaseAgent:
    """Minimal async agent base-class used across stub agents."""

    name: str = "agent"
    capabilities: list[str] = []
    version: str = "0.1"
    description: str = ""

    # ------------------------------------------------------------------
    async def run(
        self, _spec: Any, **_kwargs: Any
    ) -> dict[str, Any]:  # noqa: D401 – stub
        return {"success": True}

    async def validate(self) -> None:  # noqa: D401 – stub
        return None

    async def health_check(self) -> dict[str, str]:  # noqa: D401 – stub
        return {"status": "healthy"}


class FrostyContext:
    """In-memory orchestrator context used by the open-source tests."""

    def __init__(self) -> None:
        self.session_id: str = str(uuid.uuid4())
        self.domain: str | None = None
        self.agents: dict[str, BaseAgent] = {}

        # Sub-systems --------------------------------------------------
        self.memory = MemoryStore()
        self.planner: Any = None  # noqa: ANN401 – out of scope for stub
        self.tool_registry: Any = None  # noqa: ANN401 – stub only
        self.guardrails = Guardrails()

    # Agent management ------------------------------------------------------
    async def register_agent(
        self, name: str, agent: BaseAgent
    ) -> None:  # noqa: D401 – stub
        self.agents[name] = agent

    async def get_agent(self, name: str) -> BaseAgent:  # noqa: D401 – stub
        try:
            return self.agents[name]
        except KeyError as err:
            raise AgentNotFoundError(name) from err

    async def validate(self) -> None:  # noqa: D401 – stub
        # In real impl we would run invariants; here we just noop
        return None

    # Higher-level helpers ---------------------------------------------------
    async def build_scriptchain(
        self, *, goal: str, domain: str | None = None
    ) -> dict[str, Any]:  # noqa: D401
        return {
            "name": "script_chain",
            "goal": goal,
            "domain": domain or self.domain,
            "nodes": [],
        }

    async def emit_event(
        self, _event: str, _payload: dict[str, Any]
    ) -> None:  # noqa: D401 – stub
        await self.memory.add_memory(
            content=_event, node_type="event", metadata=_payload
        )

    async def get_relevant_context(
        self, _query: str, _agent: str
    ) -> list[dict[str, Any]]:  # noqa: D401 – stub
        return []

    async def build_agent_for_domain(
        self,
        *,
        domain: str,
        agent_type: str,
        capabilities: list[str] | None = None,
    ) -> BaseAgent:  # noqa: D401 – stub
        cls_name = f"{domain}_{agent_type}_agent"

        class _DomainAgent(BaseAgent):  # type: ignore[misc]
            name = cls_name
            capabilities = capabilities or []
            version = "0.1"
            description = f"Domain-specific agent for {domain} ({agent_type})"

            async def run(
                self, _spec: Any, **_kwargs: Any
            ) -> dict[str, Any]:  # noqa: D401 – stub
                return {"success": True, "domain": domain}

        return _DomainAgent()

    async def create_sub_context(
        self, domain: str
    ) -> "FrostyContext":  # noqa: D401 – stub
        sub = FrostyContext()
        sub.session_id = self.session_id  # share session
        sub.domain = domain
        sub.memory = self.memory  # share memory in stub implementation
        return sub
