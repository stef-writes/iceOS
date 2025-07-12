"""PDF text extraction tool."""

from __future__ import annotations

import asyncio
import io
import re
from pathlib import Path
from typing import Any, ClassVar, Dict, List

import httpx

try:  # Optional dependency – PDF extraction
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover – optional dep
    PdfReader = None  # type: ignore

from ..base import BaseTool, ToolError

_HTTP_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


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
            # Wrap raw bytes in BytesIO so *PdfReader* receives a file-like
            # object which matches its type signature (str | IO | Path).
            reader = await asyncio.to_thread(PdfReader, io.BytesIO(pdf_bytes))
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
