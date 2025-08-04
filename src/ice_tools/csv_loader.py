"""CSVLoaderTool – load a CSV file into a list of row dictionaries.

This tool is intentionally dependency-free: it uses Python's standard
``csv`` module instead of pandas so that the core toolkit does not pull heavy
data-science libraries.

It is meant as the first step in Kim's end-to-end listing workflow:
``csv_loader → listing_agent (loop) → aggregator``.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field

from ice_core.base_tool import ToolBase
from ice_core.exceptions import ValidationError
from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry

__all__: list[str] = ["CSVLoaderTool"]

logger = logging.getLogger(__name__)


class CSVLoaderTool(ToolBase):
    """Read a CSV file from local disk and return rows as dictionaries."""

    # Metadata -----------------------------------------------------------------
    name: str = "csv_loader"
    description: str = "Load a CSV file and return rows as JSON dictionaries."

    # Config -------------------------------------------------------------------
    path: str = Field(..., description="Path to CSV file (absolute or relative)")
    delimiter: str = Field(
        ",", min_length=1, max_length=1, description="Field delimiter character"
    )
    encoding: str = Field("utf-8", description="File encoding")
    max_rows: Optional[int] = Field(
        None, ge=1, description="Optional safety cap on the number of rows to load"
    )

    # ------------------------------------------------------------------
    # Execution ---------------------------------------------------------
    # ------------------------------------------------------------------
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:  # noqa: D401
        # Accept path from runtime args (from workflow tool_args) or use instance default
        runtime_path = kwargs.get("path", self.path)
        runtime_delimiter = kwargs.get("delimiter", self.delimiter)
        file_path = Path(runtime_path).expanduser().resolve()
        if not file_path.is_file():
            raise ValidationError(f"CSV file not found: {file_path}")

        rows: List[Dict[str, Any]] = []
        try:
            with file_path.open("r", encoding=self.encoding, newline="") as fp:
                reader = csv.DictReader(fp, delimiter=runtime_delimiter)
                for idx, row in enumerate(reader, start=1):
                    rows.append(dict(row))
                    if self.max_rows and idx >= self.max_rows:
                        break
        except Exception as exc:  # pragma: no cover – unexpected I/O errors
            raise ValidationError(f"Failed to read CSV: {exc}") from exc

        logger.debug("CSV loaded | path=%s rows=%s", file_path, len(rows))
        return {"rows": rows}

    # ------------------------------------------------------------------
    # Schema overrides --------------------------------------------------
    # ------------------------------------------------------------------
    @classmethod
    def get_input_schema(cls):  # noqa: D401 – override
        """CSVLoader accepts optional path override at runtime."""
        return {
            "type": "object", 
            "properties": {
                "path": {"type": "string", "description": "CSV file path (optional override)"},
                "delimiter": {"type": "string", "description": "CSV delimiter (optional override)"}
            }, 
            "additionalProperties": False
        }


# Auto-registration -----------------------------------------------------------
_instance = CSVLoaderTool(path="/dev/null")  # dummy path for registration only
registry.register_instance(NodeType.TOOL, _instance.name, _instance, validate=False)  # type: ignore[arg-type]
