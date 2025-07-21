"""BuilderAdapter – bridges legacy *workflow_builder* engine to the new
IBuilderService protocol so higher layers (ice_api) depend only on the
stable service interface instead of importing `ice_sdk.chain_builder.*`.

Placement under *ice_sdk.services* keeps layer boundaries intact: SDK is
allowed to depend on ``ice_core`` (where the protocol lives) and on its own
sub-packages, while higher layers use ServiceLocator to obtain the bound
service instance.
"""

from __future__ import annotations

from typing import Optional

from ice_core.services.contracts import IBuilderService

from ice_sdk.chain_builder.workflow_builder import (  # type: ignore
    BuilderEngine,
    ChainDraft,
    Question,
)
from ice_sdk.services.locator import ServiceLocator

__all__: list[str] = ["BuilderAdapter"]


class BuilderAdapter(IBuilderService):
    """Concrete implementation of :class:`IBuilderService`.

    The adapter is *stateless*: all state (drafts) lives in the calling layer
    (e.g. `ice_api.api.builder`).  This design keeps the service easily
    reusable and side-effect free – complying with repo rule #2.
    """

    # ------------------------------------------------------------------
    # IBuilderService implementation
    # ------------------------------------------------------------------

    def start(self, total_nodes: int, chain_name: Optional[str] = None) -> ChainDraft:  # type: ignore[override]
        return BuilderEngine.start(total_nodes=total_nodes, chain_name=chain_name)

    def next_question(self, draft: ChainDraft) -> Optional[Question]:  # type: ignore[override]
        return BuilderEngine.next_question(draft)

    def submit_answer(self, draft: ChainDraft, key: str, answer: str) -> None:  # type: ignore[override]
        BuilderEngine.submit_answer(draft, key, answer)

    def render_chain(self, draft: ChainDraft) -> str:  # type: ignore[override]
        return BuilderEngine.render_chain(draft)

    def render_mermaid(self, draft: ChainDraft) -> str:  # type: ignore[override]
        return BuilderEngine.render_mermaid(draft)


# ---------------------------------------------------------------------------
# Service registration (composition-root) -----------------------------------
# ---------------------------------------------------------------------------

ServiceLocator.register("builder_service", BuilderAdapter())
