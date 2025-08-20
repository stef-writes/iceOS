from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel, Field

from ice_api.dependencies import rate_limit
from ice_api.security import get_request_identity, require_auth
from ice_core.registry import registry

router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])  # noqa: D401


class UploadResponseItem(BaseModel):
    filename: str
    ingested_keys: List[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    scope: str
    count: int
    items: List[UploadResponseItem]


@router.post(
    "/files",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def upload_files(  # noqa: D401
    files: List[UploadFile] = File(...),
    scope: str = Form("kb"),
    chunk_size: int = Form(1000),
    overlap: int = Form(200),
    metadata_json: Optional[str] = Form(None),
) -> UploadResponse:
    """Upload one or more text files, ingest into semantic memory.

    Parameters
    ----------
    files : List[UploadFile]
            One or more files to ingest as plain text.
    scope : str
            Semantic memory scope key used for retrieval.
    chunk_size : int
            Chunk size in characters for splitting.
    overlap : int
            Overlap size between chunks.
    metadata_json : str | None
            Optional JSON string of metadata to attach to each chunk (merged with filename).
    """
    from json import loads as _loads

    from fastapi import Request as _Req

    # Identity (best-effort from request in registry context)
    org_id: Optional[str] = None
    user_id: Optional[str] = None
    try:
        req: Optional[_Req] = (
            registry._context.get("request") if hasattr(registry, "_context") else None
        )  # type: ignore[attr-defined]
        if req is not None:
            org_id, user_id = get_request_identity(req)  # type: ignore[arg-type]
    except Exception:
        pass

    base_meta: Dict[str, Any] = {}
    if metadata_json:
        try:
            base_meta = _loads(metadata_json)
        except Exception:
            base_meta = {}

    tool = registry.get_tool_instance("ingestion_tool")
    items: List[UploadResponseItem] = []
    for uf in files:
        content = (await uf.read()).decode("utf-8", errors="ignore")
        metadata = {**base_meta, "filename": uf.filename}
        result = await tool.execute(
            inputs={
                "source_type": "text",
                "source": content,
                "scope": scope,
                "chunk_size": chunk_size,
                "overlap": overlap,
                "metadata": metadata,
                "org_id": org_id,
                "user_id": user_id,
            }
        )
        # ToolBase returns dict already; tolerate both dict and potential legacy shapes
        keys: List[str]
        if isinstance(result, dict):
            keys = [e.get("key", "") for e in result.get("ingested", [])]
        else:
            keys = []
        items.append(UploadResponseItem(filename=uf.filename, ingested_keys=keys))

    return UploadResponse(scope=scope, count=len(items), items=items)
