"""Global registry for reusable *ScriptChain* instances.

Chains that should be invoked via *nested_chain* nodes or NetworkSpec files
must first be registered here.  Registration is typically done at import time
in the module that defines the chain::

    from ice_orchestrator.core.chain_registry import register_chain

    chain = build_checkout_chain()
    register_chain(chain, alias="checkout@1.0.0")

The registry intentionally lives in *ice_orchestrator* (execution layer) to
avoid *ice_sdk* —> orchestrator imports.
"""

from __future__ import annotations

from typing import Dict

# NOTE: Use WorkflowLike alias; ScriptChainLike deprecated
from ice_sdk.interfaces.chain import WorkflowLike as _WorkflowLike

# Backwards-compat alias until callers updated
ScriptChainLike = _WorkflowLike

# ---------------------------------------------------------------------------
# In-memory registry ---------------------------------------------------------
# ---------------------------------------------------------------------------

_REGISTRY: Dict[str, ScriptChainLike] = {}


# ---------------------------------------------------------------------------
# Public helpers -------------------------------------------------------------
# ---------------------------------------------------------------------------


def register_chain(
    chain: ScriptChainLike, alias: str | None = None
) -> None:  # noqa: D401
    """Register *chain* under *alias* (defaults to ``chain.name``).

    Registration overrides existing entries with the same alias.
    """

    key = alias or getattr(chain, "name", None) or getattr(chain, "chain_id", None)
    if key is None:
        raise ValueError(
            "Cannot infer alias for chain registration; please specify explicitly"
        )

    _REGISTRY[key] = chain


def get_chain(alias: str) -> ScriptChainLike | None:  # noqa: D401
    """Return chain registered under *alias* or *None* when missing."""

    return _REGISTRY.get(alias)


def list_chains() -> dict[str, ScriptChainLike]:  # noqa: D401
    """Return copy of the current registry mapping."""

    return dict(_REGISTRY)
