"""CompositeAgent groups multiple *ScriptChain* instances into a single logical
capability bundle.

This class lives in the *orchestrator* layer so that it can freely import the
chain registry without violating the SDK → Orchestrator layering contract.
"""

from __future__ import annotations

import logging
from typing import Any, List, Sequence

from ice_orchestrator.core.chain_registry import get_chain
from ice_sdk.models.node_models import ChainExecutionResult

logger = logging.getLogger(__name__)


class CompositeAgent:  # noqa: D101 – minimal public API for now
    """Lightweight wrapper delegating sequentially to a list of ScriptChains."""

    def __init__(self, chain_aliases: Sequence[str]):
        self._aliases: List[str] = list(chain_aliases)
        self._chains = []
        for alias in chain_aliases:
            chain = get_chain(alias)
            if chain is None:
                raise ValueError(
                    f"Unknown chain alias '{alias}' while building CompositeAgent"
                )
            self._chains.append(chain)

    # ------------------------------------------------------------------
    # Public helpers ----------------------------------------------------
    # ------------------------------------------------------------------
    async def act(self, payload: Any) -> ChainExecutionResult:  # noqa: D401
        """Sequentially execute all sub-chains, passing output → input."""

        context = payload
        last_result: ChainExecutionResult | None = None

        for chain in self._chains:
            logger.debug(
                "CompositeAgent executing chain '%s'",
                getattr(chain, "name", repr(chain)),
            )
            try:
                last_result = await chain.execute(initial_context=context)
            except Exception:  # pragma: no cover
                logger.error("Sub-chain failed inside CompositeAgent", exc_info=True)
                raise

            if not last_result.success:
                # Stop early on first failure – caller decides what to do.
                return last_result

            context = last_result.output

        assert last_result is not None  # for mypy – there is at least one chain
        return last_result

    # Convenience ------------------------------------------------------------
    def as_tool(self, tool_name: str, description: str = "Composite capability"):
        """Expose the entire CompositeAgent as a *Tool* for AiNode calls."""

        from ice_sdk.tools.base import BaseTool  # local import to avoid heavy deps

        agent_ref = self

        class _CompositeAgentTool(BaseTool):
            name = tool_name  # type: ignore  # noqa: A003 – override class attr
            description = description  # type: ignore

            parameters_schema = {
                "type": "object",
                "properties": {
                    "payload": {
                        "type": "object",
                        "description": "Input forwarded to the first sub-chain",
                    }
                },
                "required": ["payload"],
            }

            async def run(self, payload: Any, **_kwargs: Any):  # type: ignore[override]
                result = await agent_ref.act(payload)
                return {"success": result.success, "output": result.output}

        return _CompositeAgentTool()
