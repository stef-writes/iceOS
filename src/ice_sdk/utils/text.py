"""Light-weight helpers for text extraction & chunking.

This module deliberately stays dependency-lean – it only pulls in heavy
libraries (pypdf, python-docx) *lazily* on the specific code path that
requires them so that importing :pymod:`ice_sdk.utils` keeps an almost-zero
footprint for typical non-KB workflows.

The public surface mirrors the minimal needs of the new *KnowledgeService*:

* ``extract_text`` – convert a file to raw UTF-8 text.
* ``chunk_text``   – deterministic fixed-length splitting with overlap.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

__all__ = ["TextProcessor"]

logger = logging.getLogger(__name__)


class TextProcessor(BaseModel):  # type: ignore[misc] – Pydantic model for config reuse
    """Utility class wrapping common document-to-text helpers.

    The class is intentionally *stateless* – all heavy objects (e.g. PDF
    parsers, OCR engines) are initialised lazily inside the relevant helper
    so that creating many instances remains cheap.
    """

    # Chunking defaults (can be overridden per call) ---------------------
    default_chunk_size: int = Field(1000, ge=100, description="Size of content chunks")
    default_chunk_overlap: int = Field(200, ge=0, description="Overlap between chunks")

    # ------------------------------------------------------------------
    # Public helpers ----------------------------------------------------
    # ------------------------------------------------------------------
    def extract_text(self, file_path: Path) -> str:  # noqa: D401 – helper
        """Return **raw** text extracted from *file_path*.

        Supported formats (auto-detected by extension):
        * ``.txt`` & ``.md`` – read as UTF-8.
        * ``.pdf``          – extracted via **pypdf**.
        * ``.docx``         – extracted via **python-docx** (optional dep).

        Any unsupported or extraction failures raise *ValueError* so that
        callers can decide on fallback behaviour (e.g. skip file, alert user).
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
    ) -> List[str]:  # noqa: D401 – helper
        """Deterministically split *text* into overlapping chunks.

        The algorithm is a simple sliding window to preserve context – it is
        **deterministic** (idempotent) which is crucial for caching &
        reproducibility.
        """

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
            start = end - overlap  # slide window with overlap
        return chunks

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_pdf(file_path: Path) -> str:  # noqa: D401 – helper
        try:
            import pypdf  # type: ignore
        except ImportError as exc:  # pragma: no cover – optional dep path
            raise ValueError("pypdf must be installed to extract PDFs") from exc

        reader = pypdf.PdfReader(str(file_path))
        text_io = io.StringIO()
        for page in reader.pages:
            try:
                text_io.write(page.extract_text() or "")
                text_io.write("\n")
            except Exception:  # pragma: no cover – extraction edge cases
                continue
        return text_io.getvalue()

    @staticmethod
    def _extract_docx(file_path: Path) -> str:  # noqa: D401 – helper
        try:
            import docx  # type: ignore
        except ImportError as exc:  # pragma: no cover – optional dep path
            raise ValueError(
                "python-docx must be installed to extract DOCX files"
            ) from exc

        document = docx.Document(str(file_path))
        paragraphs = [para.text for para in document.paragraphs]
        return "\n".join(paragraphs)
