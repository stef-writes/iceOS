from __future__ import annotations

from typing import Any, Dict, List, Optional

from ice_builder.retrieval import blueprints_adapter, registry_adapter, runs_adapter
from ice_builder.retrieval.library_api_adapter import list_library_assets_via_api
from ice_core.llm.capabilities import get_capabilities
from ice_core.models.enums import ModelProvider
from ice_core.models.llm import LLMConfig
from ice_core.models.mcp import PartialBlueprint, PartialNodeSpec
from ice_core.protocols.builder import (
    DraftStoreProtocol,
    ModelPolicyProtocol,
    NodePatch,
    PatchApplierProtocol,
    PlannerProtocol,
    RetrieverProtocol,
    ToolSchemaProviderProtocol,
)


class _NoopPlanner(PlannerProtocol):
    def validate(self) -> None:
        return None

    async def plan(self, *, text: str, canvas_state: Dict[str, Any]) -> List[NodePatch]:
        # Minimal default: no-op suggestions
        return []


class _NoopRetriever(RetrieverProtocol):
    def validate(self) -> None:
        return None

    async def get_context(self, *, query: str, scopes: List[str]) -> Dict[str, Any]:
        return {"query": query, "scopes": scopes, "results": {}}


class _RegistryRetriever(RetrieverProtocol):
    def validate(self) -> None:
        return None

    async def get_context(self, *, query: str, scopes: List[str]) -> Dict[str, Any]:
        ctx: Dict[str, Any] = {"query": query}
        if "tool_schemas" in scopes:
            try:
                ctx["tool_schemas"] = await registry_adapter.list_tool_schemas()
            except Exception:
                ctx["tool_schemas"] = []
        if "blueprints" in scopes:
            try:
                ctx["blueprints"] = await blueprints_adapter.list_blueprints(limit=20)
            except Exception:
                ctx["blueprints"] = []
        if "runs" in scopes:
            try:
                ctx["runs"] = await runs_adapter.list_recent_runs(limit=20)
            except Exception:
                ctx["runs"] = []
        if "library" in scopes:
            try:
                ctx["library"] = await list_library_assets_via_api(limit=20)
            except Exception:
                ctx["library"] = []
        return ctx


class _SimplePatchApplier(PatchApplierProtocol):
    def validate(self) -> None:
        return None

    async def validate_and_apply(
        self, *, blueprint: PartialBlueprint, patches: List[NodePatch]
    ) -> PartialBlueprint:
        # Apply simple add/remove/update semantics
        for p in patches:
            p.ensure_valid()
            if p.action == "add_node" and p.node is not None:
                blueprint.add_node(p.node)
            elif p.action == "remove_node" and p.node_id:
                blueprint.nodes = [n for n in blueprint.nodes if n.id != p.node_id]
                # revalidate incrementally
                blueprint._validate_incremental()  # type: ignore[attr-defined]
            elif p.action == "update_node" and p.node_id and p.updates:
                for i, node in enumerate(blueprint.nodes):
                    if node.id == p.node_id:
                        node_dict = node.model_dump()
                        node_dict.update(p.updates)
                        blueprint.nodes[i] = PartialNodeSpec(**node_dict)
                        break
                blueprint._validate_incremental()  # type: ignore[attr-defined]
        return blueprint


class _EnvModelPolicy(ModelPolicyProtocol):
    def __init__(
        self, *, default_provider: str | None = None, default_model: str | None = None
    ):
        import os

        self._provider = default_provider or os.getenv(
            "ICE_DEFAULT_LLM_PROVIDER", "openai"
        )
        self._model = default_model or os.getenv("ICE_DEFAULT_LLM_MODEL", "gpt-4o")

    def validate(self) -> None:
        return None

    def select(self, *, task: str, constraints: Dict[str, Any]) -> LLMConfig:
        """Choose model with simple env defaults and basic capability checks.

        Accepts optional overrides in constraints: provider/model/temperature.
        Denies overrides that are not recognized by the capability registry.
        """
        provider_override = constraints.get("provider")
        model_override = constraints.get("model")

        provider_str = str(provider_override or self._provider)
        model_str = str(model_override or self._model)

        # Validate against capability registry when overrides provided
        caps = get_capabilities(provider_str.lower(), model_str.lower())
        if provider_override or model_override:
            if caps is None:
                # Fall back to env defaults if unknown; callers may surface a warning
                provider_str = str(self._provider)
                model_str = str(self._model)

        try:
            provider_enum = (
                provider_str
                if isinstance(provider_str, ModelProvider)
                else ModelProvider(provider_str)
            )
        except Exception:
            provider_enum = ModelProvider.OPENAI

        return LLMConfig(
            provider=provider_enum,
            model=model_str,
            temperature=constraints.get("temperature"),
        )


class _StaticToolSchemas(ToolSchemaProviderProtocol):
    def __init__(self, schemas: Optional[List[Dict[str, Any]]] = None) -> None:
        self._schemas = schemas or []

    def validate(self) -> None:
        return None

    async def list(self) -> List[Dict[str, Any]]:
        return list(self._schemas)


class _InMemoryDrafts(DraftStoreProtocol):
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def validate(self) -> None:
        return None

    async def put(self, *, key: str, value: Dict[str, Any]) -> None:
        self._store[key] = value

    async def get(self, *, key: str) -> Optional[Dict[str, Any]]:
        return self._store.get(key)


__all__ = [
    "_NoopPlanner",
    "_NoopRetriever",
    "_RegistryRetriever",
    "_SimplePatchApplier",
    "_EnvModelPolicy",
    "_StaticToolSchemas",
    "_InMemoryDrafts",
]
