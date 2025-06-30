from __future__ import annotations

import uuid
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ice_cli.chain_builder.engine import (  # type: ignore
    BuilderEngine,
    ChainDraft,
    Question,
)

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
    total_nodes: int = Field(..., gt=0, le=100)
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


# ---------------------------------------------------------------------------
# In-memory store -----------------------------------------------------------
# ---------------------------------------------------------------------------

_drafts: Dict[str, ChainDraft] = {}


# ---------------------------------------------------------------------------
# Helper functions ----------------------------------------------------------
# ---------------------------------------------------------------------------

def _get_draft(draft_id: str) -> ChainDraft:
    try:
        return _drafts[draft_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="draft_id not found")


# ---------------------------------------------------------------------------
# Routes --------------------------------------------------------------------
# ---------------------------------------------------------------------------


@router.post("/start", response_model=StartResponse, status_code=201)
async def start_builder(req: StartRequest):  # noqa: D401
    draft = BuilderEngine.start(total_nodes=req.total_nodes, chain_name=req.name)
    draft_id = str(uuid.uuid4())
    _drafts[draft_id] = draft
    first_q = BuilderEngine.next_question(draft)
    return StartResponse(draft_id=draft_id, question=QuestionModel.from_engine(first_q))


@router.get("/next", response_model=QuestionModel | None)
async def next_question(draft_id: str):  # noqa: D401
    draft = _get_draft(draft_id)
    q = BuilderEngine.next_question(draft)
    return QuestionModel.from_engine(q)


@router.post("/answer", response_model=AnswerResponse)
async def submit_answer(req: AnswerRequest):  # noqa: D401
    draft = _get_draft(req.draft_id)
    BuilderEngine.submit_answer(draft, req.key, req.answer)
    next_q = BuilderEngine.next_question(draft)
    completed = next_q is None and draft.current_step == 0 and len(draft.nodes) >= draft.total_nodes
    return AnswerResponse(next_question=QuestionModel.from_engine(next_q), completed=completed)


@router.get("/render", response_model=RenderResponse)
async def render_chain(draft_id: str):  # noqa: D401
    draft = _get_draft(draft_id)
    source = BuilderEngine.render_chain(draft)
    return RenderResponse(source=source)


@router.delete("/{draft_id}", status_code=204)
async def delete_draft(draft_id: str):  # noqa: D401
    _drafts.pop(draft_id, None)
    return None 