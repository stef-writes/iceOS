from __future__ import annotations

"""Factory for creating a default BuilderService with minimal implementations."""


from ice_builder.drafts.http_store import HttpDraftStore
from ice_builder.impls.minimal import (
    _EnvModelPolicy,
    _InMemoryDrafts,
    _NoopPlanner,
    _NoopRetriever,
    _RegistryRetriever,
    _SimplePatchApplier,
    _StaticToolSchemas,
)
from ice_builder.prompts.planner import PromptPlanner
from ice_builder.service import BuilderService


def create_builder_service() -> BuilderService:
    import os

    use_prompt = os.getenv("ICE_BUILDER_USE_PROMPT_PLANNER", "0") == "1"
    planner = PromptPlanner() if use_prompt else _NoopPlanner()
    use_registry_ctx = os.getenv("ICE_BUILDER_USE_REGISTRY_CONTEXT", "1") == "1"
    retriever = _RegistryRetriever() if use_registry_ctx else _NoopRetriever()
    drafts = (
        HttpDraftStore()
        if os.getenv("ICE_BUILDER_USE_HTTP_DRAFTS", "1") == "1"
        else _InMemoryDrafts()
    )
    return BuilderService(
        planner=planner,
        retriever=retriever,
        patch_applier=_SimplePatchApplier(),
        model_policy=_EnvModelPolicy(),
        tool_schemas=_StaticToolSchemas(),
        drafts=drafts,
    )


__all__ = ["create_builder_service"]
