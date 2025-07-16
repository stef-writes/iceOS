from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Response  # type: ignore
from pydantic import BaseModel, Field, conint  # type: ignore

from ice_sdk.chain_builder.engine import BuilderEngine, ChainDraft, Question

__all__ = ["router"]

router = APIRouter(prefix="/api/v1/builder", tags=["chain-builder"])


# ---------------------------------------------------------------------------
# Pydantic schemas -----------------------------------------------------------
# ---------------------------------------------------------------------------


class QuestionModel(BaseModel):
    key: str
    prompt: str
    choices: Optional[list[str]] = None

    @classmethod
    def from_engine(cls, q: Question | None) -> Optional["QuestionModel"]:
        if q is None:
            return None
        return cls(key=q.key, prompt=q.prompt, choices=q.choices)


class StartRequest(BaseModel):
    total_nodes: conint(gt=0, le=20) = Field(  # Max 20 nodes for alpha
        ..., description="Total nodes in chain (1-20)"
    )
    name: Optional[str] = None


class StartResponse(BaseModel):
    draft_id: str
    question: Optional[QuestionModel]


class AnswerRequest(BaseModel):
    draft_id: str
    key: str
    answer: str


class AnswerResponse(BaseModel):
    next_question: Optional[QuestionModel]
    completed: bool


class RenderResponse(BaseModel):
    source: str
    mermaid: str


# New – persistence -----------------------------------------------------------


class ExportResponse(BaseModel):
    draft: dict[str, Any]


class ResumeRequest(BaseModel):
    draft: dict[str, Any]  # Raw ChainDraft JSON as produced by ExportResponse


class ResumeResponse(BaseModel):
    draft_id: str
    question: Optional[QuestionModel]


# ---------------------------------------------------------------------------
# In-memory store -----------------------------------------------------------
# ---------------------------------------------------------------------------

_TTL_SECONDS = 30 * 60  # 30-minute in-memory expiry

# Map draft_id -> (ChainDraft, created_at_ts)
_drafts: Dict[str, Tuple[ChainDraft, float]] = {}


# ---------------------------------------------------------------------------
# Helper functions ----------------------------------------------------------
# ---------------------------------------------------------------------------


def _cleanup_expired() -> None:  # noqa: D401 – helper
    """Purge drafts older than the configured TTL."""
    now = time.time()
    expired = [k for k, (_, ts) in _drafts.items() if now - ts > _TTL_SECONDS]
    for k in expired:
        _drafts.pop(k, None)


def _get_draft(draft_id: str) -> ChainDraft:
    _cleanup_expired()
    try:
        draft, _ = _drafts[draft_id]
        return draft
    except KeyError:
        raise HTTPException(status_code=404, detail="draft_id not found")


# ---------------------------------------------------------------------------
# Routes --------------------------------------------------------------------
# ---------------------------------------------------------------------------


@router.post("/start", response_model=StartResponse, status_code=201)
async def start_builder(req: StartRequest) -> StartResponse:  # noqa: D401
    draft = BuilderEngine.start(total_nodes=req.total_nodes, chain_name=req.name)
    draft_id = str(uuid.uuid4())
    _drafts[draft_id] = (draft, time.time())
    first_q = BuilderEngine.next_question(draft)
    return StartResponse(draft_id=draft_id, question=QuestionModel.from_engine(first_q))


@router.get("/next", response_model=QuestionModel | None)
async def next_question(draft_id: str) -> QuestionModel | None:  # noqa: D401
    draft = _get_draft(draft_id)
    q = BuilderEngine.next_question(draft)
    return QuestionModel.from_engine(q)


@router.post("/answer", response_model=AnswerResponse)
async def submit_answer(req: AnswerRequest) -> AnswerResponse:  # noqa: D401
    draft = _get_draft(req.draft_id)

    # ------------------------------------------------------------------
    # Validation --------------------------------------------------------
    # ------------------------------------------------------------------
    q_expected = BuilderEngine.next_question(draft)
    if q_expected is None:
        raise HTTPException(
            status_code=400, detail="No question pending for this draft"
        )

    if req.key != q_expected.key:
        raise HTTPException(
            status_code=400, detail=f"Expected key '{q_expected.key}', got '{req.key}'"
        )

    if q_expected.choices and req.answer not in q_expected.choices:
        raise HTTPException(status_code=400, detail="Answer not in allowed choices")

    # Submit ------------------------------------------------------------
    BuilderEngine.submit_answer(draft, req.key, req.answer)

    next_q = BuilderEngine.next_question(draft)
    completed = (
        next_q is None
        and draft.current_step == 0
        and len(draft.nodes) >= draft.total_nodes
    )
    return AnswerResponse(
        next_question=QuestionModel.from_engine(next_q), completed=completed
    )


@router.get("/render", response_model=RenderResponse)
async def render_chain(draft_id: str) -> RenderResponse:  # noqa: D401
    draft = _get_draft(draft_id)
    source = BuilderEngine.render_chain(draft)
    mermaid = BuilderEngine.render_mermaid(draft)
    return RenderResponse(source=source, mermaid=mermaid)


@router.delete("/{draft_id}", status_code=204, response_class=Response)
async def delete_draft(draft_id: str) -> Response:  # noqa: D401
    _drafts.pop(draft_id, None)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Persistence endpoints ------------------------------------------------------
# ---------------------------------------------------------------------------


@router.get("/export", response_model=ExportResponse)
async def export_draft(draft_id: str) -> ExportResponse:  # noqa: D401
    """Return the raw ChainDraft dict so clients can persist it offline."""

    draft = _get_draft(draft_id)
    from dataclasses import asdict

    return ExportResponse(draft=asdict(draft))


@router.post("/resume", response_model=ResumeResponse, status_code=201)
async def resume_draft(req: ResumeRequest) -> ResumeResponse:  # noqa: D401
    """Load *draft* JSON (as from `/export`) and return a fresh `draft_id`."""

    # Validate and reconstruct ------------------------------------------------
    try:
        draft_obj = ChainDraft(**req.draft)  # type: ignore[arg-type]
    except TypeError as exc:  # noqa: BLE001 – explicit catch
        raise HTTPException(status_code=400, detail=f"Invalid draft payload: {exc}")

    draft_id = str(uuid.uuid4())
    _drafts[draft_id] = (draft_obj, time.time())

    next_q = BuilderEngine.next_question(draft_obj)
    return ResumeResponse(draft_id=draft_id, question=QuestionModel.from_engine(next_q))


# ---------------------------------------------------------------------------
# Admin convenience: manual cleanup ----------------------------------------
# ---------------------------------------------------------------------------


@router.post("/cleanup", status_code=204, response_class=Response)
async def cleanup() -> Response:  # noqa: D401
    """Delete all expired drafts (older than TTL)."""
    _cleanup_expired()
    return Response(status_code=204)
