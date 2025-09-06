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

        # Baseline defaults
        self._provider: str = str(
            default_provider or os.getenv("ICE_DEFAULT_LLM_PROVIDER", "openai")
        )
        self._model: str = str(
            default_model or os.getenv("ICE_DEFAULT_LLM_MODEL", "gpt-4o")
        )

        # Preferred candidates (capability-checked in select). Format:
        #   ICE_PREFERRED_LLM_MODELS="openai:gpt-5,openai:gpt-4o-mini,anthropic:claude-3-5-sonnet"
        preferred_raw = os.getenv("ICE_PREFERRED_LLM_MODELS", "")
        self._preferred: list[tuple[str, str]] = []
        if preferred_raw.strip():
            for item in preferred_raw.split(","):
                tok = item.strip()
                if not tok:
                    continue
                if ":" in tok:
                    prov, mod = tok.split(":", 1)
                    self._preferred.append((prov.strip(), mod.strip()))
                else:
                    # Assume provider default if only model supplied
                    self._preferred.append((self._provider, tok))
        else:
            # Sensible built-ins: try cutting-edge first, then stable, then env defaults
            self._preferred = [
                ("openai", "gpt-5"),
                ("openai", "gpt-4o-mini"),
                ("openai", "gpt-4o"),
                ("anthropic", "claude-3-5-sonnet"),
                (self._provider, self._model),
            ]

    def validate(self) -> None:
        return None

    def select(self, *, task: str, constraints: Dict[str, Any]) -> LLMConfig:
        """Choose model using preferred list with capability-based fallback.

        Constraints may include provider/model/temperature. We evaluate:
        1) explicit override (if capability-supported)
        2) preferred list (env ICE_PREFERRED_LLM_MODELS or sensible defaults)
        3) final fallback to env defaults
        """
        # 1) Explicit overrides
        override_provider = constraints.get("provider")
        override_model = constraints.get("model")
        if override_provider or override_model:
            p = str(override_provider or self._provider)
            m = str(override_model or self._model)
            if get_capabilities(p.lower(), m.lower()) is not None:
                try:
                    prov_enum = p if isinstance(p, ModelProvider) else ModelProvider(p)
                except Exception:
                    prov_enum = ModelProvider.OPENAI
                return LLMConfig(
                    provider=prov_enum,
                    model=m,
                    temperature=constraints.get("temperature"),
                )
            # fall through to preferred if override unsupported

        # 2) Preferred list
        for prov, mod in self._preferred:
            if not prov or not mod:
                continue
            if get_capabilities(prov.lower(), mod.lower()) is not None:
                try:
                    prov_enum = (
                        prov if isinstance(prov, ModelProvider) else ModelProvider(prov)
                    )
                except Exception:
                    prov_enum = ModelProvider.OPENAI
                return LLMConfig(
                    provider=prov_enum,
                    model=mod,
                    temperature=constraints.get("temperature"),
                )

        # 3) Final fallback to env defaults (even if capability lookup failed)
        try:
            env_enum = (
                self._provider
                if isinstance(self._provider, ModelProvider)
                else ModelProvider(self._provider)
            )
        except Exception:
            env_enum = ModelProvider.OPENAI
        return LLMConfig(
            provider=env_enum,
            model=self._model,
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
