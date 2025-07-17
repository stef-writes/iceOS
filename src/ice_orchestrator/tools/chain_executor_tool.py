"""orchestrator.tools.chain_executor_tool

Run a registered `ScriptChain` as if it were a regular LLM tool.

`ChainExecutorTool` resolves the chain via
:pymeth:`ice_orchestrator.core.chain_registry.get_chain` and forwards an (optional)
input payload as the chain’s *initial context*.

Why in *orchestrator*?
----------------------
Look-ups and execution depend on orchestrator internals (registry & executor),
so placing the tool here avoids an illegal import edge from `ice_sdk` to
`ice_orchestrator`.

Example
-------
```python
from ice_orchestrator.core.chain_registry import register_chain
from ice_orchestrator.tools.chain_executor_tool import ChainExecutorTool

register_chain(my_chain, alias="my_chain@1")

tool = ChainExecutorTool(alias="my_chain@1")
result = await tool.run()
print(result)
```
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from pydantic import Field, field_validator

from ice_orchestrator.core.chain_registry import get_chain
from ice_sdk.models.node_models import ChainExecutionResult
from ice_sdk.tools.base import BaseTool, ToolError

__all__: list[str] = ["ChainExecutorTool"]


class ChainExecutorTool(BaseTool):
    """Execute a registered `ScriptChain` inside a tool-call boundary.

    Parameters
    ----------
    alias : str
        Registry alias of the target ScriptChain.
    input : dict[str, Any], optional
        Initial context forwarded to the chain.  Defaults to empty dict.
    """

    # Metadata -----------------------------------------------------------------
    name: ClassVar[str] = "chain_executor"
    description: ClassVar[str] = "Run a registered ScriptChain as an atomic tool"
    tags: ClassVar[list[str]] = ["workflow", "chain", "orchestration"]

    # JSON schema for tool parameters -----------------------------------------
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "alias": {
                "type": "string",
                "description": "Registry alias of the ScriptChain to execute",
            },
            "input": {
                "type": "object",
                "description": "Initial context forwarded to the ScriptChain",
                "additionalProperties": True,
            },
        },
        "required": ["alias"],
    }

    # Pydantic runtime validation ---------------------------------------------
    alias: str = Field(..., description="Registry alias of the ScriptChain")
    input: Dict[str, Any] = Field(
        default_factory=dict,
        description="Initial context forwarded to the ScriptChain",
    )

    @field_validator("alias")
    @classmethod
    def _alias_not_empty(cls, v: str) -> str:  # noqa: D401
        if not v.strip():
            raise ValueError("alias must be non-empty")
        return v

    # Output schema is intentionally wide open – sub-chains decide structure ---
    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "output": {"description": "Output from the ScriptChain"},
            "success": {"type": "boolean"},
        },
        "required": ["success"],
    }

    # ---------------------------------------------------------------------
    # validate() is inherited – pydantic handles field validation ---------
    # ---------------------------------------------------------------------

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        """Invoke the chain and return its success flag and output.

        Returns
        -------
        dict[str, Any]
            ``{"success": bool, "output": Any}``

        Raises
        ------
        ToolError
            If the alias is unknown or the chain raises an exception.
        """

        alias: str = kwargs.get("alias", self.alias)
        input_payload: Dict[str, Any] = kwargs.get("input", self.input)

        chain = get_chain(alias)
        if chain is None:
            raise ToolError(f"Chain alias '{alias}' is not registered")

        try:
            result: ChainExecutionResult = await chain.execute(  # type: ignore[assignment]
                initial_context=input_payload
            )
        except Exception as exc:  # pragma: no cover – runtime errors
            raise ToolError(f"Nested chain execution failed: {exc}") from exc

        return {
            "success": result.success,
            "output": result.output,
        }
