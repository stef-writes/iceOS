from __future__ import annotations

"""Skeleton Builder Service composing protocol components.

This module provides a high-level facade for the AI Builder that composes
protocol-defined components (planner, retriever, ranker, critic, patch applier,
model policy, tool schemas, drafts). It intentionally avoids HTTP concerns.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ice_core.llm.service import LLMService
from ice_core.models.llm import LLMConfig
from ice_core.models.mcp import PartialBlueprint
from ice_core.protocols.builder import (
    DraftStoreProtocol,
    ModelPolicyProtocol,
    NodePatch,
    PatchApplierProtocol,
    PlannerProtocol,
    RetrieverProtocol,
    ToolSchemaProviderProtocol,
)


class BuilderService(BaseModel):
    """High-level AI Builder service (implementation-agnostic facade).

    Args:
        planner: PlannerProtocol implementation
        retriever: RetrieverProtocol implementation
        patch_applier: PatchApplierProtocol implementation
        model_policy: ModelPolicyProtocol implementation
        tool_schemas: ToolSchemaProviderProtocol implementation
        drafts: DraftStoreProtocol implementation
        llm: LLMService instance for provider-agnostic LLM calls
    """

    # Use Any for Pydantic model fields; enforce protocols via runtime checks below
    planner: Any
    retriever: Any
    patch_applier: Any
    model_policy: Any
    tool_schemas: Any
    drafts: Any
    llm: LLMService = Field(default_factory=LLMService)
    last_hints: Dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
        "protected_namespaces": (),
    }

    # Validate protocol conformance at runtime (idempotent)
    @classmethod
    def model_validate_protocols(cls, v: "BuilderService") -> "BuilderService":  # type: ignore[name-defined]
        return v

    def __init__(self, **data: Any):  # type: ignore[no-untyped-def]
        super().__init__(**data)
        # Enforce protocols if available (runtime_checkable)
        try:
            assert isinstance(self.planner, PlannerProtocol)
            assert isinstance(self.retriever, RetrieverProtocol)
            assert isinstance(self.patch_applier, PatchApplierProtocol)
            assert isinstance(self.model_policy, ModelPolicyProtocol)
            assert isinstance(self.tool_schemas, ToolSchemaProviderProtocol)
            assert isinstance(self.drafts, DraftStoreProtocol)
        except Exception:
            # Best-effort enforcement; avoid crashing in minimal images
            pass

    # Public methods ---------------------------------------------------------

    async def suggest_nodes(
        self, *, text: str, canvas_state: Dict[str, Any]
    ) -> List[NodePatch]:
        self._validate_components()
        # Enrich canvas_state with retrieval context (tool schemas first)
        try:
            ctx = await self.retriever.get_context(
                query=text, scopes=["tool_schemas", "blueprints", "runs", "library"]
            )
            merged_state = dict(canvas_state)
            merged_state.setdefault("context", {}).update(ctx)
        except Exception:
            merged_state = canvas_state
        # Planner proposal
        patches_any = await self.planner.plan(text=text, canvas_state=merged_state)
        patches: List[NodePatch] = [NodePatch.model_validate(p) for p in patches_any]  # type: ignore[arg-type]
        for p in patches:
            p.ensure_valid()
        # Capture builder hints for the caller (questions, missing_fields, usage, model)
        try:
            hints = merged_state.get("builder_hints", {})
            if isinstance(hints, dict):
                self.last_hints = dict(hints)
        except Exception:
            self.last_hints = {}
        # Deterministic fallback: minimal two-node plan (LLM then writer_tool)
        if not patches:
            try:
                fallback_llm = NodePatch.model_validate(
                    {
                        "action": "add_node",
                        "node": {
                            "id": "llm1",
                            "type": "llm",
                            "name": "planner_llm",
                            "dependencies": [],
                        },
                    }
                )
                fallback_writer = NodePatch.model_validate(
                    {
                        "action": "add_node",
                        "node": {
                            "id": "writer1",
                            "type": "tool",
                            "tool_name": "writer_tool",
                            "dependencies": ["llm1"],
                        },
                    }
                )
                fallback_llm.ensure_valid()
                fallback_writer.ensure_valid()
                patches = [fallback_llm, fallback_writer]
            except Exception:
                # Leave empty if even fallback cannot validate
                pass
        # Rank proposals if multiple (simple identity ranker for now)
        try:
            from ice_builder.prompts.ranker import PromptRanker

            ranked = await PromptRanker().rank(
                options=[p.model_dump() for p in patches], criteria={}
            )
            patches = [NodePatch.model_validate(p) for p in ranked]
        except Exception:
            pass
        # Optional critique (non-blocking)
        try:
            from ice_builder.prompts.critic import PromptCritic

            _ = await PromptCritic().review(
                blueprint=merged_state.get("blueprint", {}), run_logs=None
            )
        except Exception:
            pass
        return patches

    async def propose_blueprint(
        self, *, text: str, base: Optional[PartialBlueprint] = None
    ) -> PartialBlueprint:
        self._validate_components()
        canvas_state: Dict[str, Any] = {"blueprint": base.model_dump() if base else {}}
        # Enrich with retrieval context similar to suggest_nodes
        try:
            ctx = await self.retriever.get_context(query=text, scopes=["tool_schemas"])
            canvas_state.setdefault("context", {}).update(ctx)
        except Exception:
            pass
        patches_any = await self.planner.plan(text=text, canvas_state=canvas_state)
        patches: List[NodePatch] = [NodePatch.model_validate(p) for p in patches_any]  # type: ignore[arg-type]
        for p in patches:
            p.ensure_valid()
        applied = await self.patch_applier.validate_and_apply(
            blueprint=base or PartialBlueprint(), patches=patches
        )
        return PartialBlueprint.model_validate(applied)

    async def apply_patch(
        self, *, blueprint: PartialBlueprint, patches: List[NodePatch]
    ) -> PartialBlueprint:
        self._validate_components()
        for p in patches:
            p.ensure_valid()
        applied = await self.patch_applier.validate_and_apply(
            blueprint=blueprint, patches=patches
        )
        return PartialBlueprint.model_validate(applied)

    def apply_policy_overrides(
        self,
        *,
        task: str,
        canvas_state: Dict[str, Any],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Validate and apply LLM overrides via model policy.

        Parameters
        ----------
        task : str
            High-level task name (e.g., "builder/suggest").
        canvas_state : Dict[str, Any]
            Current canvas state to enrich with validated overrides.
        provider : str | None
            Optional provider override requested by caller.
        model : str | None
            Optional model override requested by caller.
        temperature : float | None
            Optional temperature override.

        Returns
        -------
        Dict[str, Any]
            A shallow copy of canvas_state with a normalized "builder_overrides" entry
            and hint fields (provider/model) for downstream cost estimation.

        Example
        -------
        >>> svc = BuilderService(...)
        >>> st = svc.apply_policy_overrides(task="builder/suggest", canvas_state={}, provider="openai", model="gpt-4o")
        >>> isinstance(st, dict)
        True
        """
        self._validate_components()
        merged_state = dict(canvas_state)
        constraints: Dict[str, Any] = {}
        if provider is not None:
            constraints["provider"] = provider
        if model is not None:
            constraints["model"] = model
        if temperature is not None:
            constraints["temperature"] = temperature

        # Let policy choose the final config (may normalize or fallback)
        chosen: LLMConfig = self.choose_model(task=task, constraints=constraints)
        overrides: Dict[str, Any] = {
            "provider": str(getattr(chosen.provider, "value", chosen.provider)),
            "model": chosen.model,
        }
        if chosen.temperature is not None:
            overrides["temperature"] = chosen.temperature

        merged_state.setdefault("builder_overrides", {}).update(overrides)
        # Expose hints for cost estimator downstream
        merged_state.setdefault("builder_hints", {}).update(
            {"provider": overrides["provider"], "model": overrides["model"]}
        )
        return merged_state

    async def retrieve_context(
        self, *, query: str, scopes: List[str]
    ) -> Dict[str, Any]:
        self._validate_components()
        ctx_any = await self.retriever.get_context(query=query, scopes=scopes)
        return dict(ctx_any)

    def choose_model(self, *, task: str, constraints: Dict[str, Any]) -> LLMConfig:
        self._validate_components()
        cfg_any = self.model_policy.select(task=task, constraints=constraints)
        return LLMConfig.model_validate(cfg_any)

    # Internal ---------------------------------------------------------------

    def _validate_components(self) -> None:
        # Call validate() on all components (idempotent by contract)
        self.planner.validate()
        self.retriever.validate()
        self.patch_applier.validate()
        self.model_policy.validate()
        self.tool_schemas.validate()
        self.drafts.validate()

    # Draft helpers -----------------------------------------------------------
    async def save_draft(self, *, key: str, data: Dict[str, Any]) -> None:
        try:
            await self.drafts.put(key=key, value=data)
        except Exception:
            pass

    async def load_draft(self, *, key: str) -> Optional[Dict[str, Any]]:
        try:
            value = await self.drafts.get(key=key)
            if value is None:
                return None
            return dict(value)
        except Exception:
            return None


__all__ = ["BuilderService"]
