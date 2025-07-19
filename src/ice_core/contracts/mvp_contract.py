"""Minimal, JSON-friendly contract exposing core orchestrator capabilities.

This *MVP* surface purposefully keeps the API tiny – just enough for
CLI/HTTP wrappers and low-code consumers to:

1.  **execute_chain** – run a workflow defined as a JSON payload
2.  **register_skill** – add a new skill at runtime (validated)
3.  **cost_estimate** – return a rough USD cost prediction for a workflow

All methods use *plain* Python primitives (dict/str/float) so that callers
in any language can serialise over JSON without importing ice-internal
classes.

Strategic alignment:
    • Rule 11 – single stable service interface.
    • Rule 13 – validation happens in one place before execution.
    • YC-MVP – consolidates scattered helpers behind a micro façade.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Literal

from pydantic import BaseModel, model_validator

from ice_core.models.enums import ModelProvider
from ice_orchestrator.core.chain_factory import ChainFactory
from ice_sdk.providers.costs import get_price_per_token
from ice_sdk.skills.base import SkillBase
from ice_sdk.skills.registry import global_skill_registry

__all__: list[str] = ["MVPContract"]


class MVPContract(BaseModel):
    """Versioned façade around orchestrator + skill registry."""

    version: Literal["0.1.0"] = "0.1.0"

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
    }

    # ------------------------------------------------------------------
    # Public – synchronous wrappers ------------------------------------
    # ------------------------------------------------------------------
    def execute_chain(self, chain_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Run *chain_spec* and return a JSON-serialisable result.

        The call blocks the current thread.  Internally it delegates to
        an async helper and manages the event-loop lifecycle so that the
        caller does not need to be async-aware.
        """

        return asyncio.run(self._execute_chain_async(chain_spec))

    def register_skill(self, name: str, skill: SkillBase) -> bool:  # noqa: D401
        """Register *skill* under *name* after validation.

        Returns ``True`` on success, raises ``SkillRegistrationError`` on
        duplicate or invalid registrations (propagated from registry).
        """

        # Ensure skill passes its own validation contract (Rule 13)
        if hasattr(skill, "validate") and not skill.validate(
            getattr(skill, "config", {})  # type: ignore[arg-type]
        ):
            raise ValueError(f"Skill '{name}' failed self-validation")

        global_skill_registry.register(name, skill)
        return True

    def cost_estimate(self, chain_spec: Dict[str, Any]) -> float:  # noqa: D401
        """Rough USD cost estimation for *chain_spec*.

        Heuristic:
            • For every AI (LLM) node assume:
              *prompt_tokens* = 0.5 × *max_tokens* (default 1 000)
              *completion_tokens* = max_tokens.
            • Multiply by pricing table from :pymod:`ice_sdk.providers.costs`.

        This keeps the implementation dependency-free while remaining
        directionally useful for budget gating.
        """

        total_cost_usd = 0.0
        for node in chain_spec.get("nodes", []):
            node_type = node.get("type")
            if node_type not in {"ai", "llm"}:
                continue  # Only AI nodes incur per-token cost

            provider_str: str = node.get("provider", ModelProvider.OPENAI.value)
            try:
                provider = ModelProvider(provider_str)
            except ValueError:
                provider = ModelProvider.OPENAI

            model_name: str = node.get("model", "gpt-4o")
            max_tokens: int = int(node.get("max_tokens", 2000) or 2000)
            # Heuristic prompt/comp split
            prompt_toks = max_tokens // 2
            completion_toks = max_tokens

            prompt_price, completion_price = get_price_per_token(provider, model_name)
            total_cost_usd += float(
                prompt_price * prompt_toks + completion_price * completion_toks
            )

        return round(total_cost_usd, 6)

    # ------------------------------------------------------------------
    # Internal helpers – async -----------------------------------------
    # ------------------------------------------------------------------
    async def _execute_chain_async(self, chain_spec: Dict[str, Any]) -> Dict[str, Any]:
        chain = await ChainFactory.from_dict(chain_spec)
        result = await chain.execute()
        # ``model_dump`` returns plain JSON-serialisable objects with pydantic v2
        return result.model_dump(mode="json")

    # ------------------------------------------------------------------
    # Idempotent validation (Rule 13) ----------------------------------
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def _post_init(self) -> "MVPContract":  # noqa: D401 – pydantic hook
        # For v0.1 no extra fields to validate – placeholder for future.
        return self
