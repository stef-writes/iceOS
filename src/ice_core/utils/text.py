"""Deterministic summarisation helpers (moved from summariser.py)."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field

__all__ = [
    "deterministic_summariser",
    "TextProcessor",
]


def deterministic_summariser(
    content: Any,
    *,
    schema: Dict[str, Any] | None = None,
    max_tokens: int | None = None,
) -> str:
    import json

    try:
        text = (
            content
            if isinstance(content, str)
            else json.dumps(content, ensure_ascii=False, default=str)
        )
    except Exception:
        text = str(content)
    if max_tokens is None:
        max_tokens = 400
    char_budget = max_tokens * 4
    if len(text) <= char_budget:
        return text
    return text[: char_budget - 3] + "…"


logger = logging.getLogger(__name__)


class TextProcessor(BaseModel):  # type: ignore[misc]
    """Utility class wrapping common document-to-text helpers.

    The class is intentionally *stateless* – heavy dependencies (e.g. PDF
    parsers, OCR engines) are loaded lazily so that instantiation remains
    cheap for non-KB scenarios.
    """

    default_chunk_size: int = Field(1000, ge=100, description="Size of content chunks")
    default_chunk_overlap: int = Field(200, ge=0, description="Overlap between chunks")

    # ------------------------------------------------------------------
    # Public helpers ----------------------------------------------------
    # ------------------------------------------------------------------
    def extract_text(self, file_path: Path) -> str:
        """Return UTF-8 text extracted from *file_path*.

        Supported formats (auto-detected by extension):
          * .txt / .md – read as UTF-8
          * .pdf       – extracted via *pypdf*
          * .docx      – extracted via *python-docx*
        """

        suffix = file_path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            return self._extract_pdf(file_path)
        if suffix == ".docx":
            return self._extract_docx(file_path)
        raise ValueError(f"Unsupported file type for text extraction: {file_path}")

    def chunk_text(
        self,
        text: str,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> List[str]:
        """Deterministically split *text* into overlapping chunks."""

        size = chunk_size or self.default_chunk_size
        overlap = chunk_overlap or self.default_chunk_overlap
        if size <= 0:
            raise ValueError("chunk_size must be > 0")
        if overlap >= size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        tokens: list[str] = text.split()
        if not tokens:
            return []

        chunks: list[str] = []
        start = 0
        while start < len(tokens):
            end = min(start + size, len(tokens))
            chunk = " ".join(tokens[start:end])
            chunks.append(chunk.strip())
            if end == len(tokens):
                break
            start = end - overlap
        return chunks

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_pdf(file_path: Path) -> str:
        try:
            import pypdf  # type: ignore
        except ImportError as exc:
            raise ValueError("pypdf must be installed to extract PDFs") from exc

        reader = pypdf.PdfReader(str(file_path))
        text_io = io.StringIO()
        for page in reader.pages:
            try:
                text_io.write(page.extract_text() or "")
                text_io.write("\n")
            except Exception:  # pragma: no cover
                continue
        return text_io.getvalue()

    @staticmethod
    def _extract_docx(file_path: Path) -> str:
        try:
            import docx  # type: ignore
        except ImportError as exc:
            raise ValueError(
                "python-docx must be installed to extract DOCX files"
            ) from exc

        document = docx.Document(str(file_path))
        paragraphs = [para.text for para in document.paragraphs]
        return "\n".join(paragraphs)
