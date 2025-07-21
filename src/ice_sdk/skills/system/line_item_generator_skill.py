from __future__ import annotations

"""line_item_generator_skill – LLM turns natural-language request into structured CSV row."""

import json
from typing import Any, ClassVar, Dict, Literal

from pydantic import BaseModel, Field, field_validator

from ice_core.models.llm import LLMConfig, ModelProvider

from ...providers.llm_service import LLMService
from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__: list[str] = ["LineItemGeneratorSkill"]


class LineGenInput(BaseModel):
    request_text: str = Field(..., min_length=10)
    headers: Any  # accept list or string

    @field_validator("headers")
    @classmethod
    def _parse_headers(cls, v):  # noqa: D401
        if isinstance(v, str):
            try:
                import ast

                return list(ast.literal_eval(v))
            except Exception:
                return [h.strip() for h in v.strip("[]").split(",") if h]
        return v


class LineGenOutput(BaseModel):
    row: Dict[str, Any]
    action: Literal["append", "update", "delete"]


class LineItemGeneratorSkill(SkillBase):
    name: str = "line_item_generator"
    description: str = (
        "LLM converts a plain-English request into a structured CSV row + action."
    )

    InputModel: ClassVar[type[BaseModel]] = LineGenInput
    OutputModel: ClassVar[type[BaseModel]] = LineGenOutput

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        try:
            inp = self.InputModel(**kwargs)
        except Exception as exc:
            raise SkillExecutionError(f"Invalid input: {exc}") from exc

        prompt = (
            "You are an inventory assistant. The CSV has columns: "
            f"{', '.join(inp.headers)}.\n"
            "Interpret the user request below and output **only** valid JSON with keys: \n"
            "  row – object mapping each column to a value (string).\n"
            "  action – one of 'append', 'update', 'delete'.\n\n"
            f"User request:\n{inp.request_text}\n\n"
            'Example:\n{"row":{...},"action":"append"}'
        )

        llm_cfg = LLMConfig(  # type: ignore[call-arg]
            provider=ModelProvider.OPENAI.value,
            model="gpt-4o",
            max_tokens=256,
            temperature=0.2,
        )

        text, _usage, err = await LLMService().generate(llm_cfg, prompt)
        if err:
            raise SkillExecutionError(err)

        # Some models wrap output in markdown fences – strip if present.
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # drop leading fence (``` or ```json)
            cleaned = (
                cleaned.split("\n", 1)[1]
                if "\n" in cleaned
                else cleaned.lstrip("`json")
            )
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]

        try:
            obj = json.loads(cleaned)
            row = obj["row"]
            action = obj["action"]
        except Exception as e:
            raise SkillExecutionError(
                f"LLM output not valid JSON: {e}; raw: {text[:120]}"
            ) from e

        return {"row": row, "action": action}
