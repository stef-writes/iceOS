from __future__ import annotations

"""RowsValidatorTool – validate tabular rows before summarisation.

The tool checks that each row contains the *required_columns* and optionally
filters out invalid rows.  It returns a flag, an error list (if any) and a
JSON-serialisable string of the cleaned rows so downstream nodes can consume
it via template placeholders.
"""

import json
from typing import Any, ClassVar, Dict, List, Type, Union

from pydantic import BaseModel, Field, field_validator

from ...utils.errors import ToolExecutionError
from ..base import ToolBase

__all__: list[str] = ["RowsValidatorTool"]

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

class RowsValidatorTool(ToolBase):
    """Validate tabular rows before summarisation."""

    name: str = "rows_validator"
    description: str = "Validate rows contain required columns"
    
    InputModel: ClassVar[Type[BaseModel]] = RowsValidatorInput
    OutputModel: ClassVar[Type[BaseModel]] = RowsValidatorOutput

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        input_data = RowsValidatorInput(**kwargs)
        
        errors: List[str] = []
        cleaned_rows: List[Dict[str, Any]] = []
        
        if not isinstance(input_data.rows, list):
            raise ToolExecutionError("rows_validator", "rows must be a list")
            
        for idx, row in enumerate(input_data.rows):
            if not isinstance(row, dict):
                errors.append(f"Row {idx} is not a dictionary")
                continue
                
            missing_cols = [col for col in input_data.required_columns if col not in row]
            if missing_cols:
                errors.append(f"Row {idx} missing columns: {missing_cols}")
                if not input_data.drop_invalid:
                    continue
            else:
                cleaned_rows.append(row)
                
        valid = len(errors) == 0
        return {
            "valid": valid,
            "cleaned_count": len(cleaned_rows),
            "errors": errors,
            "clean_rows_json": json.dumps(cleaned_rows) if cleaned_rows else None
        }
