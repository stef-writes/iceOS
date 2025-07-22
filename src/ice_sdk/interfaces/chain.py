from __future__ import annotations

from typing import Any, Protocol, TypeAlias


class ScriptChainLike(Protocol):
    """Minimal subset of ice_orchestrator.workflow.Workflow (formerly *ScriptChain*) used by ice_sdk.

    Having this protocol inside ice_sdk lets us keep type hints while
    avoiding a real import from the higher-level *ice_orchestrator* layer.
    Only attributes actually accessed by the SDK should be listed here.
    """

    # Public-ish attributes accessed by ice_sdk --------------------------------
    context_manager: Any
    _agent_cache: dict[str, Any]
    _chain_tools: list[Any]

    # Methods that are directly invoked ---------------------------------------
    # (currently none; extend when needed)


# Temporary alias during the *ScriptChain* → *Workflow* migration -------------
# Once all internal references have been updated, this can be removed.
WorkflowLike: TypeAlias = ScriptChainLike  # type: ignore

# NOTE: To avoid an import cycle, we import AgentNode lazily in TYPE_CHECKING
# blocks by using a forward reference string above.
