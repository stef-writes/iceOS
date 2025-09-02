from __future__ import annotations

"""Prompt-based planner (optional) implementing PlannerProtocol.

Gated by env in the factory; defaults to Noop planner to avoid requiring
provider keys in tests.
"""

from typing import Any, Dict, List

from ice_builder.prompts.pack import PlannerPromptPack, default_planner_pack
from ice_core.llm.service import LLMService
from ice_core.models.enums import ModelProvider
from ice_core.models.llm import LLMConfig
from ice_core.protocols.builder import NodePatch, PlannerProtocol

_SYSTEM = (
    "You are an expert workflow architect. Given a user request and context, "
    "propose a minimal set of NodePatch operations to update a PartialBlueprint.\n"
    "Output STRICT JSON with a top-level array of patches. Each patch has:\n"
    '{"action": "add_node|remove_node|update_node", "node": PartialNodeSpec?, "node_id": str?, "updates": object?}.\n'
    "Do not include commentary."
)


class PromptPlanner(PlannerProtocol):
    def __init__(
        self,
        *,
        llm: LLMService | None = None,
        pack: PlannerPromptPack | None = None,
        default_provider: str | None = None,
        default_model: str | None = None,
    ) -> None:
        self._llm = llm or LLMService()
        self._pack = pack or default_planner_pack()
        # Soft defaults; a real policy should be injected via ModelPolicyProtocol
        self._provider = default_provider or "openai"
        self._model = default_model or "gpt-4o"

    def validate(self) -> None:
        # Nothing to validate for the skeleton; provider presence checked at call time
        return None

    async def plan(self, *, text: str, canvas_state: Dict[str, Any]) -> List[NodePatch]:
        # Compose prompt
        # Attach any retrieval context injected into canvas_state (e.g., tool_schemas)
        user = self._pack.user_template.format(request=text, canvas_state=canvas_state)
        # Choose model with optional overrides from canvas_state
        overrides = canvas_state.get("builder_overrides", {})
        provider_str = (
            overrides.get("provider") if isinstance(overrides, dict) else None
        ) or self._provider
        model_str = (
            overrides.get("model") if isinstance(overrides, dict) else None
        ) or self._model
        temperature = (
            overrides.get("temperature") if isinstance(overrides, dict) else None
        )
        try:
            provider_enum = ModelProvider(provider_str)
        except Exception:
            provider_enum = ModelProvider.OPENAI
        cfg = LLMConfig(
            provider=provider_enum, model=model_str, temperature=temperature or 0
        )
        # Call LLM (best-effort); on error, return empty suggestions
        text_out, usage, err = await self._llm.generate(
            llm_config=cfg, prompt=self._pack.system + "\n\n" + user, context={}
        )
        if err or not text_out:
            return []
        # Parse JSON array of patches safely
        import json

        try:
            raw = json.loads(text_out)
            # Support object shape { patches: [...], questions?: [...], missing_fields?: {...} }
            candidate_patches: List[Any]
            questions: List[str] = []
            missing_fields: Dict[str, Any] = {}
            if isinstance(raw, dict):
                candidate_patches = raw.get("patches", [])
                if isinstance(raw.get("questions"), list):
                    questions = [str(q) for q in raw["questions"]]
                if isinstance(raw.get("missing_fields"), dict):
                    missing_fields = dict(raw["missing_fields"])  # shallow copy
                # Attach hints back onto canvas_state for downstream consumers
                canvas_state.setdefault("builder_hints", {})
                canvas_state["builder_hints"].update(
                    {
                        "questions": questions,
                        "missing_fields": missing_fields,
                        "usage": usage or {},
                        "provider": provider_enum.value,
                        "model": model_str,
                    }
                )
            else:
                candidate_patches = raw

            patches: List[NodePatch] = [
                NodePatch.model_validate(p) for p in candidate_patches
            ]
            for p in patches:
                p.ensure_valid()
            return patches
        except Exception:
            return []


__all__ = ["PromptPlanner"]
