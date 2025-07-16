from __future__ import annotations

# ruff: noqa: E402

"""Runtime capability catalog.

Aggregates the various *per-type* registries (tools, chains, node modes and
agents) into a single read-only view so UIs and HTTP/CLI layers can query all
capabilities from one place.

The catalog **does not** replace the existing registries – it merely mirrors
(and periodically refreshes from) them.  Each capability is represented by a
:class:`~ice_sdk.capabilities.card.CapabilityCard` so callers receive a uniform
schema irrespective of the underlying kind.

Layering rules
--------------
* Lives under the top-level ``iceos`` package so it may import from both
  ``ice_sdk`` and ``ice_orchestrator`` without violating the *SDK → Orchestrator*
  layering boundary.
* Has *no* external side-effects unless callers explicitly invoke
  :py:meth:`CapabilityCatalog.persist`.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from ice_sdk.capabilities.card import CapabilityCard, KindLiteral  # noqa: F401
from ice_sdk.capabilities.registry import CapabilityRegistry
from ice_sdk.node_registry import NODE_REGISTRY
from ice_sdk.services import ServiceLocator
from ice_sdk.tools.service import ToolService

# Optional imports guarded – the orchestrator layer may not be present in all
# runtime contexts (e.g. minimal lambda functions).
try:  # pragma: no cover – optional dependency
    from ice_orchestrator.core import chain_registry  # type: ignore
except Exception:  # noqa: BLE001 – defensive import
    chain_registry = None  # type: ignore


class CatalogSummary(BaseModel):
    """Lightweight JSON-serialisable overview of the catalog."""

    tools: List[str]
    chains: List[str]
    nodes: List[str]
    agents: List[str]


class CapabilityCatalog:  # noqa: D101 – simple façade
    _registry: CapabilityRegistry

    # ------------------------------------------------------------------
    # Construction & refresh -------------------------------------------
    # ------------------------------------------------------------------
    def __init__(self, *, auto_refresh: bool = True) -> None:  # noqa: D401
        self._registry = CapabilityRegistry()
        # Track chain aliases discovered via the orchestrator (populated in _collect_chains)
        self._chain_aliases: List[str] = []
        if auto_refresh:
            self.refresh()

    # ------------------------------------------------------------------
    # Public helpers ----------------------------------------------------
    # ------------------------------------------------------------------
    def refresh(self) -> None:  # noqa: D401 – mutate internal state
        """Clear & rebuild the internal registry from live data sources."""

        # Reset----------------------------------------------------------------------
        self._registry = CapabilityRegistry()

        # Collect data from each registry -------------------------------------------
        self._collect_tools()
        self._collect_chains()
        self._collect_nodes()
        self._collect_agents()

    def list(self) -> List[CapabilityCard]:  # noqa: D401 – proxy helper
        return self._registry.list()

    def search(self, query: str) -> List[CapabilityCard]:  # noqa: D401 – proxy
        return self._registry.search(query)

    def get(self, id_: str) -> Optional[CapabilityCard]:  # noqa: D401 – proxy
        return self._registry.get(id_)

    # JSON-friendly summary --------------------------------------------
    def summary(self) -> CatalogSummary:  # noqa: D401
        """Return high-level lists only (cheap)."""

        tools = [c.id for c in self._registry.list() if c.kind == "tool"]

        # Chains are stored in the registry with kind=="other" but their IDs must match
        # the aliases discovered in `_collect_chains`.
        chains = [
            c.id
            for c in self._registry.list()
            if c.kind == "other" and c.id in self._chain_aliases
        ]

        # Remaining "other" kind cards that are *not* chains are considered node modes.
        nodes = [
            c.id
            for c in self._registry.list()
            if c.kind == "other" and c.id not in self._chain_aliases
        ]

        agents = [c.id for c in self._registry.list() if c.kind == "agent"]
        return CatalogSummary(tools=tools, chains=chains, nodes=nodes, agents=agents)

    # ------------------------------------------------------------------
    # Persistence (optional) -------------------------------------------
    # ------------------------------------------------------------------
    def persist(self, path: str | Path) -> None:  # noqa: D401 – side-effect
        """Write a JSON dump to *path* (best-effort; no locking)."""

        import json

        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        with path_obj.open("w", encoding="utf-8") as fh:
            json.dump([c.model_dump() for c in self._registry.list()], fh, indent=2)

    # ------------------------------------------------------------------
    # Internals ---------------------------------------------------------
    # ------------------------------------------------------------------
    def _collect_tools(self) -> None:
        try:
            tool_service: ToolService = ServiceLocator.get("tool_service")  # type: ignore[assignment]
        except KeyError:
            tool_service = ToolService()
        for card in tool_service.cards():
            self._registry.add(card, overwrite=True)

    def _collect_chains(self) -> None:  # noqa: D401 – helper
        if chain_registry is None:  # pragma: no cover – orchestrator missing
            return
        chains: Dict[str, Any] = chain_registry.list_chains()
        # Persist alias list for quick look‐up elsewhere (e.g. summary())
        self._chain_aliases = list(chains.keys())
        for alias, chain in chains.items():
            card = CapabilityCard(
                id=alias,
                kind="other",  # no dedicated literal yet
                name=getattr(chain, "name", alias) or alias,
                description=getattr(chain, "description", ""),
                tags=["chain"],
            )
            self._registry.add(card, overwrite=True)

    def _collect_nodes(self) -> None:  # noqa: D401 – helper
        for mode in NODE_REGISTRY.keys():
            card = CapabilityCard(
                id=f"node:{mode}",
                kind="other",
                name=f"Node mode '{mode}'",
                description="Executor for custom node type",
                tags=["node"],
            )
            self._registry.add(card, overwrite=True)

    def _collect_agents(self) -> None:  # noqa: D401 – helper
        try:
            ctx_mgr = ServiceLocator.get("context_manager")
        except KeyError:  # pragma: no cover – context manager not initialised
            return
        try:
            agent_names = ctx_mgr.list_agents()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 – fallback when method missing
            return
        for name in agent_names:
            card = CapabilityCard(
                id=f"agent:{name}",
                kind="agent",
                name=name,
                description="Runtime Agent",
            )
            self._registry.add(card, overwrite=True)


# ---------------------------------------------------------------------------
# Global helper -------------------------------------------------------------
# ---------------------------------------------------------------------------


def get_catalog(*, refresh: bool = False) -> CapabilityCatalog:  # noqa: D401
    """Return a singleton *CapabilityCatalog* registered in the ServiceLocator."""

    try:
        catalog: CapabilityCatalog = ServiceLocator.get("capability_catalog")  # type: ignore[assignment]
    except KeyError:
        catalog = CapabilityCatalog(auto_refresh=True)
        ServiceLocator.register("capability_catalog", catalog)
        return catalog

    if refresh:
        catalog.refresh()
    return catalog
