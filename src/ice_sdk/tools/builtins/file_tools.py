"""Generic file-handling tools (CSV, JSON, PDF) usable across multiple domains.

All external side-effects (disk / network I-O) occur **inside** the *Tool* implementations
in compliance with project rules.
"""

from __future__ import annotations

import asyncio
import base64
import csv
import json
import re
from pathlib import Path
from typing import Any, ClassVar, Dict, List

import httpx

try:  # Optional dependency – PDF extraction
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover – optional dep
    PdfReader = None  # type: ignore

try:  # Optional dependency for JMESPath queries
    import jmespath  # type: ignore
except Exception:  # pragma: no cover – optional dep
    jmespath = None  # type: ignore

from ..base import BaseTool, ToolError

__all__ = [
    "CsvLoaderTool",
    "JsonQueryTool",
    "PdfExtractTool",
]

_HTTP_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


# ---------------------------------------------------------------------------
#  CSV Loader ----------------------------------------------------------------
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
#  JSON Query ----------------------------------------------------------------
# ---------------------------------------------------------------------------
class JsonQueryTool(BaseTool):
    """Run a JMESPath query against JSON data from string, file or URL."""

    name: ClassVar[str] = "json_query"
    description: ClassVar[str] = "Query JSON using JMESPath expressions"

    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "JMESPath expression to evaluate",
            },
            "source": {
                "type": "string",
                "description": "JSON string, file path or URL",
            },
            "max_bytes": {
                "type": "integer",
                "default": 32768,
                "minimum": 256,
                "maximum": 262144,
                "description": "Maximum bytes of JSON result to return",
            },
            "base64": {
                "type": "boolean",
                "default": False,
                "description": "Encode result body as base64 string",
            },
        },
        "required": ["query", "source"],
    }

    tags: ClassVar[List[str]] = ["json", "query", "data"]

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "result": {},  # type: ignore[typeddict-item]
            "truncated": {"type": "boolean"},
        },
        "required": ["result", "truncated"],
    }

    async def _load_source(self, source: str) -> Any:  # noqa: ANN401 – dynamic JSON
        # Fast heuristic – if starts with '{' or '[' treat as inline JSON string.
        if source.strip().startswith(("{", "[")):
            return json.loads(source)
        if _HTTP_PATTERN.match(source):  # Remote fetch
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(source)
                res.raise_for_status()
                return res.json()
        # Else treat as local path ----------------------------
        try:
            text = await asyncio.to_thread(Path(source).read_text, encoding="utf-8")
            return json.loads(text)
        except FileNotFoundError as exc:
            raise ToolError(f"File not found: {source}") from exc

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        if jmespath is None:  # pragma: no cover – missing optional dep
            raise ToolError("'jmespath' package is required for JsonQueryTool")

        query_expr: str = kwargs.get("query")  # type: ignore[assignment]
        source: str = kwargs.get("source")  # type: ignore[assignment]
        if not query_expr:
            raise ToolError("'query' argument is required")
        if not source:
            raise ToolError("'source' argument is required")

        max_bytes: int = kwargs.get("max_bytes", 32768)
        wants_b64: bool = kwargs.get("base64", False)

        data = await self._load_source(source)

        try:
            compiled = jmespath.compile(query_expr)
            result = compiled.search(data)
        except Exception as exc:  # noqa: BLE001 – user query errors
            raise ToolError(f"JMESPath evaluation failed: {exc}") from exc

        # Serialise & size-check -------------------------------------------
        raw_bytes = json.dumps(result, ensure_ascii=False, default=str).encode()
        truncated = False
        if len(raw_bytes) > max_bytes:
            truncated = True
            raw_bytes = raw_bytes[:max_bytes]

        if wants_b64:
            body = base64.b64encode(raw_bytes).decode()
        else:
            body = raw_bytes.decode(errors="replace")

        return {"result": body, "truncated": truncated}


# ---------------------------------------------------------------------------
#  PDF Extract ---------------------------------------------------------------
# ---------------------------------------------------------------------------
class PdfExtractTool(BaseTool):
    """Extract plain-text from a PDF document located at file path or URL."""

    name: ClassVar[str] = "pdf_extract"
    description: ClassVar[str] = "Extract text from PDF documents"

    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "File path or URL of the PDF document",
            },
            "max_pages": {
                "type": "integer",
                "default": 10,
                "minimum": 1,
                "maximum": 200,
                "description": "Maximum number of pages to read",
            },
            "max_chars": {
                "type": "integer",
                "default": 10000,
                "minimum": 256,
                "maximum": 200000,
                "description": "Maximum characters to return",
            },
        },
        "required": ["source"],
    }

    tags: ClassVar[List[str]] = ["file", "pdf", "text"]

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "num_pages": {"type": "integer"},
            "truncated": {"type": "boolean"},
        },
        "required": ["text", "num_pages", "truncated"],
    }

    async def _load_pdf_bytes(self, source: str) -> bytes:
        if _HTTP_PATTERN.match(source):
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.get(source)
                res.raise_for_status()
                return res.content
        # Local file
        try:
            return await asyncio.to_thread(Path(source).read_bytes)
        except FileNotFoundError as exc:
            raise ToolError(f"File not found: {source}") from exc

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        if PdfReader is None:  # pragma: no cover – optional dep missing
            raise ToolError("'pypdf' package is required for PdfExtractTool")

        source: str = kwargs.get("source")  # type: ignore[assignment]
        if not source:
            raise ToolError("'source' argument is required")

        max_pages: int = kwargs.get("max_pages", 10)
        max_chars: int = kwargs.get("max_chars", 10000)

        pdf_bytes = await self._load_pdf_bytes(source)

        try:
            reader = await asyncio.to_thread(PdfReader, pdf_bytes)
        except Exception as exc:  # pragma: no cover – corrupted PDF
            raise ToolError(f"Failed to parse PDF: {exc}") from exc

        num_pages = len(reader.pages)
        text_fragments: List[str] = []
        for idx, page in enumerate(reader.pages):
            if idx >= max_pages:
                break
            try:
                text_fragments.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001 – skip problematic pages
                continue

        full_text = "\n".join(text_fragments)
        truncated = False
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars]
            truncated = True

        return {"text": full_text, "num_pages": num_pages, "truncated": truncated}
