from __future__ import annotations

"""RowsValidatorSkill – validate tabular rows before summarisation.

The skill checks that each row contains the *required_columns* and optionally
filters out invalid rows.  It returns a flag, an error list (if any) and a
JSON-serialisable string of the cleaned rows so downstream nodes can consume
it via template placeholders.
"""

import json
from typing import Any, ClassVar, Dict, List, Union

from pydantic import BaseModel, Field, field_validator

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__: list[str] = ["RowsValidatorSkill"]


class RowsValidatorInput(BaseModel):
    """Input schema for the validator."""

    rows: Union[List[Dict[str, Any]], str] = Field(..., description="Rows data")
    required_columns: List[str] = Field(default_factory=list)
    drop_invalid: bool = Field(
        default=True,
        description="Drop rows that fail validation instead of raising an error.",
    )

    # Accept JSON-encoded string for rows -----------------------------------
    @field_validator("rows")
    @classmethod
    def _parse_rows(cls, value: Union[str, List[Dict[str, Any]]]):  # noqa: D401
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception as exc:
                raise ValueError(f"rows is not valid JSON: {exc}") from exc
        return value


class RowsValidatorOutput(BaseModel):
    """Result schema."""

    valid: bool
    cleaned_count: int = Field(0, ge=0)
    errors: List[str] = Field(default_factory=list)
    clean_rows_json: str | None = None


class RowsValidatorSkill(SkillBase):
    """Skill that validates list-of-dict rows structure."""

    name: str = "rows_validator"
    description: str = "Validate row dictionaries and optionally drop invalid ones."

    InputModel: ClassVar[type[BaseModel]] = RowsValidatorInput
    OutputModel: ClassVar[type[BaseModel]] = RowsValidatorOutput

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        try:
            inp = self.InputModel(**kwargs)
        except Exception as exc:
            raise SkillExecutionError(f"Invalid RowsValidator input: {exc}") from exc

        errors: List[str] = []
        cleaned: List[Dict[str, Any]] = []

        for idx, row in enumerate(inp.rows):  # type: ignore[attr-defined]
            missing = [
                col
                for col in inp.required_columns
                if col not in row or row[col] in ("", None)
            ]
            if missing:
                msg = f"Row {idx} missing columns: {', '.join(missing)}"
                if inp.drop_invalid:
                    errors.append(msg)
                    continue  # skip row
                else:
                    raise SkillExecutionError(msg)
            cleaned.append(row)

        clean_json = json.dumps(cleaned, ensure_ascii=False)
        return {
            "valid": len(errors) == 0,
            "cleaned_count": len(cleaned),
            "errors": errors,
            "clean_rows_json": clean_json,
        }
