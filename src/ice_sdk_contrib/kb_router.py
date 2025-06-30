from __future__ import annotations

# ruff: noqa: E402

"""FastAPI router exposing a **mock** knowledge-base upload & ingestion API.

Endpoints:
    POST /api/v1/kb/upload  – store raw file on disk and returns *file_id*.
    POST /api/v1/kb/ingest/{file_id} – naïvely text-splits & appends to a
        plaintext index (used by the `KBSearchTool`).

This is intended for demos and e2e tests; replace the internals with a real
vector DB when moving to production.
"""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

__all__ = ["router"]

router = APIRouter(prefix="/api/v1/kb", tags=["knowledge-base"])

# ---------------------------------------------------------------------------
# Config --------------------------------------------------------------------
# ---------------------------------------------------------------------------

KB_ROOT: Path = Path("knowledge_base")  # Lazily created on first request

# ---------------------------------------------------------------------------
# Schemas -------------------------------------------------------------------
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    file_id: str = Field(..., description="UUID assigned to the stored file")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")


class IngestResponse(BaseModel):
    ok: bool
    chunks: int = Field(..., description="Number of textual chunks indexed (mock)")


# ---------------------------------------------------------------------------
# Internals -----------------------------------------------------------------
# ---------------------------------------------------------------------------

def _ensure_kb_dir() -> None:  # noqa: D401 – helper
    """Ensure `knowledge_base/` directory exists."""
    KB_ROOT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Routes --------------------------------------------------------------------
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:  # noqa: D401
    """Persist *file* and return a generated `file_id`."""

    _ensure_kb_dir()

    file_id = str(uuid4())
    orig_filename: str = file.filename or "upload.bin"
    dest_path = KB_ROOT / f"{file_id}_{orig_filename}"

    content = await file.read()
    dest_path.write_bytes(content)

    return UploadResponse(file_id=file_id, filename=orig_filename, size=len(content))


@router.post("/ingest/{file_id}", response_model=IngestResponse)
async def ingest_file(file_id: str) -> IngestResponse:  # noqa: D401
    """Very simple ingest that splits lines and appends to `.mock_index.txt`."""

    _ensure_kb_dir()

    matches = [p for p in KB_ROOT.iterdir() if p.name.startswith(file_id)]
    if not matches:
        raise HTTPException(status_code=404, detail="File ID not found")

    source_path = matches[0]

    try:
        text = source_path.read_text(encoding="utf-8", errors="ignore")
    except UnicodeDecodeError:
        return IngestResponse(ok=False, chunks=0)

    chunks = [line.strip() for line in text.splitlines() if line.strip()]

    index_path = KB_ROOT / ".mock_index.txt"
    with index_path.open("a", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(chunk + "\n")

    return IngestResponse(ok=True, chunks=len(chunks)) 