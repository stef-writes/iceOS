"""CSV data loading tool."""

from __future__ import annotations

import asyncio
import csv
import re
from pathlib import Path
from typing import Any, ClassVar, Dict, List

import httpx

from ..base import BaseTool, ToolError

_HTTP_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


class CsvLoaderTool(BaseTool):
    """Load a CSV file from local disk or HTTP(S) URL and return its rows.

    By default only the first *100* rows are returned – tweak *max_rows* if
    callers need more (bounded by 10k for safeguards).
    """

    name: ClassVar[str] = "csv_loader"
    description: ClassVar[str] = "Load CSV from file/URL and return rows as objects"

    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "Path or URL of the CSV file",
            },
            "delimiter": {
                "type": "string",
                "default": ",",
                "description": "CSV delimiter (single character)",
            },
            "max_rows": {
                "type": "integer",
                "default": 100,
                "minimum": 1,
                "maximum": 10000,
                "description": "Maximum number of rows to return",
            },
            "encoding": {
                "type": "string",
                "default": "utf-8",
                "description": "File encoding",
            },
        },
        "required": ["source"],
    }

    tags: ClassVar[List[str]] = ["file", "csv", "data"]

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "rows": {"type": "array", "items": {"type": "object"}},
            "truncated": {"type": "boolean"},
        },
        "required": ["rows", "truncated"],
    }

    async def _fetch_remote(self, url: str, encoding: str) -> str:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url)
            res.raise_for_status()
            return res.content.decode(encoding)

    async def _read_local(self, path: str, encoding: str) -> str:
        return await asyncio.to_thread(Path(path).read_text, encoding=encoding)

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        source: str = kwargs.get("source")  # type: ignore[assignment]
        if not source:
            raise ToolError("'source' argument is required")

        delimiter: str = kwargs.get("delimiter", ",")
        if len(delimiter) != 1:
            raise ToolError("'delimiter' must be a single character")

        max_rows: int = kwargs.get("max_rows", 100)
        if not (1 <= max_rows <= 10000):
            raise ToolError("'max_rows' must be between 1 and 10 000")

        encoding: str = kwargs.get("encoding", "utf-8")

        # Obtain CSV content -------------------------------------------------
        try:
            if _HTTP_PATTERN.match(source):
                raw_csv = await self._fetch_remote(source, encoding)
            else:
                raw_csv = await self._read_local(source, encoding)
        except FileNotFoundError as exc:
            raise ToolError(f"File not found: {source}") from exc
        except httpx.HTTPError as exc:  # pragma: no cover – network issues
            raise ToolError(f"Failed to fetch remote CSV: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise ToolError(f"Unable to load CSV: {exc}") from exc

        # Parse CSV ---------------------------------------------------------
        rows: List[Dict[str, str]] = []
        reader = csv.DictReader(raw_csv.splitlines(), delimiter=delimiter)
        for idx, row in enumerate(reader):
            if idx >= max_rows:
                break
            rows.append(dict(row))

        truncated = reader.line_num - 1 > len(rows)  # reader.line_num includes header
        return {"rows": rows, "truncated": truncated}
