from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from ice_api.security import require_auth
from ice_core.llm.service import LLMService
from ice_core.models.enums import ModelProvider
from ice_core.models.llm import LLMConfig

router = APIRouter(
    prefix="/api/v1/diag", tags=["diag"], dependencies=[Depends(require_auth)]
)


@router.get("/llm")
async def diag_llm(
    provider: str = Query(
        ..., description="Provider id (openai|anthropic|google|deepseek)"
    ),
    model: str = Query(..., description="Model name (e.g., gpt-4o)"),
) -> Dict[str, Any]:
    try:
        # Normalize provider to enum; fall back to error on invalid
        try:
            provider_enum = ModelProvider(provider)
        except Exception:
            return {"ok": False, "error": f"Unsupported provider: {provider}"}

        cfg = LLMConfig(provider=provider_enum, model=model, temperature=0)
        text, usage, err = await LLMService().generate(
            llm_config=cfg,
            prompt="diagnostic: respond with the single word OK",
            context={},
            timeout_seconds=15,
            max_retries=1,
        )
        if err:
            return {"ok": False, "error": err, "usage": usage}
        return {"ok": True, "preview": (text or "").strip()[:64], "usage": usage}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


__all__ = ["router"]
