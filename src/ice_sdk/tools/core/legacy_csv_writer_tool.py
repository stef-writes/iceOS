from __future__ import annotations

"""csv_writer_tool – append/update/delete a row in a CSV file in a thread-safe way."""

import asyncio
import csv
import json
from pathlib import Path
from typing import Any, ClassVar, Dict, Literal

from pydantic import BaseModel, Field, field_validator

from ...utils.errors import ToolExecutionError
from ..base import ToolBase

__all__: list[str] = ["CSVWriterTool"]

# Accept either raw dict or JSON string for row
class CSVWriterInput(BaseModel):
    file_path: str
    row: Any  # Dict or str JSON
    action: Literal["append", "update", "delete"] = "append"
    key_column: str = Field("Item_ID", min_length=1)

    @field_validator("file_path")
    @classmethod
    def _validate_path(cls, v: str) -> str:
        if not Path(v).exists():
            raise ValueError(f"CSV file not found: {v}")
        return v

class CSVWriterOutput(BaseModel):
    success: bool
    rows_json: str

class CSVWriterTool(ToolBase):
    name: str = "csv_writer"
    description: str = (
        "Append, update, or delete a row in a CSV file and return updated dataset."
    )

    InputModel: ClassVar[type[BaseModel]] = CSVWriterInput
    OutputModel: ClassVar[type[BaseModel]] = CSVWriterOutput

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        try:
            inp = self.InputModel(**kwargs)
        except Exception as exc:
            raise ToolExecutionError("csv_writer", f"Invalid CSVWriter input: {exc}") from exc

        path = Path(inp.file_path)

        # Coerce row ----------------------------------------------------
        row_obj: Dict[str, Any]
        if isinstance(inp.row, str):
            try:
                row_obj = json.loads(inp.row)
            except Exception:
                try:
                    import ast

                    row_obj = ast.literal_eval(inp.row)
                except Exception as exc:
                    raise ToolExecutionError(
                        f"row string could not be parsed as JSON or literal dict: {exc}"
                    ) from exc
        else:
            row_obj = inp.row  # type: ignore[assignment]

        # Heavy I/O in background thread -----------------------------------
        def _mutate_csv() -> list[Dict[str, Any]]:
            # Read---------------------------------------------------------
            with path.open(newline="") as fh:
                reader = list(csv.DictReader(fh))
                headers = reader[0].keys() if reader else row_obj.keys()

            data: list[Dict[str, Any]] = list(reader)

            # Apply action ------------------------------------------------
            if inp.action == "append":
                data.append(row_obj)
            else:
                # Need key matching
                key_val = row_obj.get(inp.key_column)
                idx = next(
                    (i for i, r in enumerate(data) if r.get(inp.key_column) == key_val),
                    None,
                )
                if idx is None and inp.action != "append":
                    raise ValueError("Row with key not found for update/delete")
                if inp.action == "update":
                    data[idx] = row_obj  # type: ignore[index]
                elif inp.action == "delete":
                    data.pop(idx)

            # Write--------------------------------------------------------
            with path.open("w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
            return data

        rows = await asyncio.to_thread(_mutate_csv)
        return {"success": True, "rows_json": json.dumps(rows, ensure_ascii=False)}
