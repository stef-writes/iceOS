from __future__ import annotations

"""LineItemGeneratorOperator – converts natural‐language inventory requests into structured row + action.

This is the LLMOperator replacement for the deprecated `line_item_generator_tool`.
"""

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, field_validator

from ice_orchestrator.llm.operators.base import LLMOperator, LLMOperatorConfig
from ice_orchestrator.providers.llm_service import LLMService

__all__: list[str] = [
    "LineItemGeneratorOperator",
]

class _Input(BaseModel):
    """Validated input schema.

    Attributes
    ----------
    request_text: str
        Plain-English user request (≥10 characters)
    headers: List[str]
        Column names of the target CSV.  Accepts list or stringified list.
    """

    request_text: str = Field(..., min_length=10)
    headers: List[str]

    @field_validator("headers", mode="before")
    @classmethod
    def _parse_headers(cls, v: Any) -> List[str]:  # noqa: D401 — validator
        if isinstance(v, str):
            try:
                import ast

                return list(ast.literal_eval(v))
            except Exception:
                return [h.strip() for h in v.strip("[]").split(",") if h]
        return v

class _Output(BaseModel):
    """Structured operator output."""

    row: Dict[str, Any]
    action: Literal["append", "update", "delete"]

class LineItemGeneratorOperator(LLMOperator):
    """LLM-backed operator that emits a CSV row spec + action.

    Example
    -------
    >>> op = LineItemGeneratorOperator()
    >>> await op.process({"request_text": "Add 5 bananas", "headers": ["item", "qty"]})
    {'row': {'item': 'bananas', 'qty': '5'}, 'action': 'append'}
    """

    # Public identifiers --------------------------------------------------
    name: str = "line_item_generator"
    description: str = (
        "LLM converts a plain-English request into a structured CSV row + action."
    )

    # Explicit schemas (used by downstream validation) --------------------
    InputModel: type[_Input] = _Input
    OutputModel: type[_Output] = _Output

    # Default configuration (can be overridden at instantiation) ----------
    def __init__(
        self,
        *,
        config: LLMOperatorConfig | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        super().__init__(config=config or LLMOperatorConfig())
        self.llm_service: LLMService = llm_service or LLMService()

    # ------------------------------------------------------------------
    # Processor interface ------------------------------------------------
    # ------------------------------------------------------------------
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        """Validate *data*, call the LLM, and return structured output."""

        inp = self.InputModel(**data)

        prompt = (
            "You are an inventory assistant. The CSV has columns: "
            f"{', '.join(inp.headers)}.\n"
            "Interpret the user request below and output **only** valid JSON with keys: \n"
            "  row – object mapping each column to a value (string).\n"
            "  action – one of 'append', 'update', 'delete'.\n\n"
            f"User request:\n{inp.request_text}\n\n"
            "Example:\n{'row':{...},'action':'append'}"
        )

        # Generate text via shared helper ----------------------------------
        text = await self.generate(prompt)

        # Clean possible markdown fences ------------------------------------
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = (
                cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned.lstrip("`json")
            )
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]

        import json

        try:
            obj = json.loads(cleaned)
            row = obj["row"]
            action = obj["action"]
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"LLM output not valid JSON: {cleaned[:120]}") from exc

        output = {"row": row, "action": action}
        # Validate against OutputModel to be safe ---------------------------
        self.OutputModel(**output)
        return output

 