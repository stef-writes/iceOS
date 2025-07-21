from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, ClassVar, Type

from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..base import SkillBase
from ...utils.errors import SkillExecutionError


class CSVReaderInput(BaseModel):
    """Input schema for CSVReaderSkill."""

    file_path: str = Field(..., description="Path to the CSV file to read")
    delimiter: str = Field(",", min_length=1, max_length=1, description="CSV delimiter character")

    # ------------------------------------------------------------------
    # Runtime validation ------------------------------------------------
    # ------------------------------------------------------------------
    @field_validator("file_path")
    @classmethod
    def _validate_path(cls, v: str) -> str:  # noqa: D401 – internal helper
        if not Path(v).exists():
            raise ValueError(f"CSV file not found: {v}")
        return v


class CSVReaderOutput(BaseModel):
    """Output schema for CSVReaderSkill."""

    headers: list[str] = Field(..., description="CSV column names")
    rows: list[dict[str, Any]] = Field(..., description="Parsed row data")
    rows_json: str = Field(..., description="JSON-serialized rows for chaining")


class CSVReaderSkill(SkillBase):
    """Read a CSV file and return its rows as dictionaries."""

    name: str = "csv_reader"
    description: str = "Read a CSV file and return its rows as dictionaries."
    
    # Remove model_config and use proper ClassVar syntax
    InputModel: ClassVar[Type[BaseModel]] = CSVReaderInput
    OutputModel: ClassVar[Type[BaseModel]] = CSVReaderOutput

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:  # noqa: D401
        """Async wrapper that performs blocking I/O in a thread."""

        # ------------------------------------------------------------------
        # Step 1 – Validate & coerce input via Pydantic ---------------------
        # ------------------------------------------------------------------
        try:
            input_data = self.InputModel(**kwargs)
        except Exception as exc:
            raise SkillExecutionError(f"Invalid CSVReaderSkill input: {exc}") from exc

        path = Path(input_data.file_path)

        # ------------------------------------------------------------------
        # Step 2 – Heavy I/O moved to background thread --------------------
        # ------------------------------------------------------------------
        def _read_csv() -> tuple[list[str], list[dict[str, Any]]]:
            with path.open(newline="") as fh:
                reader = csv.DictReader(fh, delimiter=input_data.delimiter)
                rows = list(reader)
                headers: list[str] = reader.fieldnames or []
                return headers, rows

        headers, rows = await asyncio.to_thread(_read_csv)

        return {
            "headers": headers,
            "rows": rows,
            "total_rows": len(rows),
            "rows_json": json.dumps(rows, ensure_ascii=False),
        } 