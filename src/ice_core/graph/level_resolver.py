"""Branch gating resolver for ScriptChain execution.

Extracted from the original `ScriptChain._is_node_active` implementation.  The
behaviour is *identical* but lives in a dedicated, test-friendly module.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ice_core.models.node_models import ConditionNodeConfig  # avoid heavy import cycles


class BranchGatingResolver:
    def __init__(self, nodes: Mapping[str, Any], graph: Any) -> None:
        # We keep references to the chain's *nodes* mapping and *DependencyGraph*
        self._nodes = nodes
        self._graph = graph
        # Decision cache keyed by *condition node id* → bool
        self._branch_decisions: Dict[str, bool] = {}
        # Memoisation cache: node_id → bool (active?)
        self._active_cache: Dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Mutation helpers --------------------------------------------------
    # ------------------------------------------------------------------

    def record_decision(self, condition_node_id: str, decision: bool) -> None:
        """Persist the runtime outcome of *condition_node_id* and invalidate caches."""

        self._branch_decisions[str(condition_node_id)] = decision
        # Conservative approach – drop memoisation; will be recomputed lazily
        self._active_cache.clear()

    # ------------------------------------------------------------------
    # Query helpers -----------------------------------------------------
    # ------------------------------------------------------------------

    def is_node_active(self, node_id: str) -> bool:  # – helper
        """Return *True* when *node_id* should run given current branch decisions."""

        # 1. Explicit branch gating ------------------------------------
        for cond_id, decision in self._branch_decisions.items():
            cond_cfg = self._nodes.get(cond_id)
            if not isinstance(cond_cfg, ConditionNodeConfig):
                continue

            if decision and cond_cfg.false_branch and node_id in cond_cfg.false_branch:
                return False
            if (
                not decision
                and cond_cfg.true_branch
                and node_id in cond_cfg.true_branch
            ):
                return False

        # 2. Propagation via dependencies ------------------------------
        if node_id in self._active_cache:
            return self._active_cache[node_id]

        deps = self._graph.get_node_dependencies(node_id)
        for dep_id in deps:
            if not self.is_node_active(dep_id):
                self._active_cache[node_id] = False
                return False

        self._active_cache[node_id] = True
        return True

    # ------------------------------------------------------------------
    # Exposed internals (for B/C) --------------------------------------
    # ------------------------------------------------------------------

    @property
    def branch_decisions(self) -> Dict[str, bool]:
        return self._branch_decisions

    @property
    def active_cache(self) -> Dict[str, bool]:
        return self._active_cache
