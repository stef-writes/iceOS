"""orchestrator.agents.composite_agent

CompositeAgent groups multiple pre-registered `ScriptChain` instances and
executes them sequentially.

The module deliberately lives **inside** the `ice_orchestrator` package so it
can freely import the chain registry without violating the project’s *layer
boundaries* (SDK → Orchestrator is forbidden, Orchestrator → SDK is OK).

Example
-------
```python
from ice_orchestrator.core.chain_registry import register_chain
from ice_orchestrator.agents.composite_agent import CompositeAgent

# Assume ``build_checkout_chain()`` returns a ScriptChain object
register_chain(build_checkout_chain(), alias="checkout@1")

agent = CompositeAgent(["checkout@1"])
result = await agent.act({"order_id": 123})
print(result.success, result.output)
```
"""

from __future__ import annotations

import logging
from typing import Any, List, Sequence

from ice_orchestrator.core.chain_registry import get_chain
from ice_sdk.models.node_models import ChainExecutionResult

logger = logging.getLogger(__name__)


class CompositeAgent:  # noqa: D101 – minimal public API for now
    """Sequential executor for a list of `ScriptChain` aliases.

    Parameters
    ----------
    chain_aliases : Sequence[str]
        Aliases that must already be registered in
        :pymeth:`ice_orchestrator.core.chain_registry.register_chain`.

    Attributes
    ----------
    _aliases : list[str]
        Copy of the provided aliases.
    _chains : list[ScriptChainLike]
        Resolved chain objects in execution order.
    """

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
        """Run all chains with *payload* threaded through.

        The *output* of each chain becomes the *input* of the next one.

        Parameters
        ----------
        payload : Any
            Initial context forwarded to the first chain.

        Returns
        -------
        ChainExecutionResult
            Result object returned from **the last** chain in the sequence.
        """

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
        """Return a `BaseTool` facade that delegates to :pyfunc:`act`.

        Parameters
        ----------
        tool_name : str
            Name under which the generated tool will be exposed to the LLM.
        description : str, default "Composite capability"
            Short human-readable description shown in tool lists.

        Returns
        -------
        BaseTool
            *Concrete* subclass whose ``run`` method awaits :pyfunc:`act`.
        """

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
