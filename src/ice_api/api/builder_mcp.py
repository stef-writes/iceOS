from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ice_api.dependencies import rate_limit
from ice_api.errors import BuilderPlanError, BuilderPolicyViolation
from ice_api.security import require_auth
from ice_builder.factory import create_builder_service
from ice_builder.service import BuilderService
from ice_builder.toolkit.cost_estimator import CostEstimator
from ice_core.models.mcp import PartialBlueprint
from ice_core.protocols.builder import NodePatch

router = APIRouter(
    prefix="/api/v1/builder", tags=["builder"], dependencies=[Depends(require_auth)]
)


class SuggestRequest(BaseModel):
    text: str
    canvas_state: Dict[str, Any] = Field(default_factory=dict)
    # Optional model overrides for UI/Studio consumers
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None


class SuggestResponse(BaseModel):
    patches: List[NodePatch]
    questions: Optional[List[str]] = None
    missing_fields: Optional[Dict[str, Any]] = None
    cost_estimate_usd: Optional[float] = None


class ProposeRequest(BaseModel):
    text: str
    base: Optional[PartialBlueprint] = None


class ProposeResponse(BaseModel):
    blueprint: PartialBlueprint


class ApplyRequest(BaseModel):
    blueprint: PartialBlueprint
    patches: List[NodePatch]


class ApplyResponse(BaseModel):
    blueprint: PartialBlueprint


def _svc(request: Request) -> BuilderService:
    # For now create a default service per request (stateless components)
    # Later we can wire a singleton via app.state
    return create_builder_service()


@router.post(
    "/suggest", response_model=SuggestResponse, dependencies=[Depends(rate_limit)]
)
async def suggest(
    req: SuggestRequest, service: BuilderService = Depends(_svc)
) -> SuggestResponse:
    try:
        # Validate and apply overrides through model policy (no silent bypass)
        if req.provider or req.model or req.temperature is not None:
            req.canvas_state = service.apply_policy_overrides(
                task="builder/suggest",
                canvas_state=req.canvas_state,
                provider=req.provider,
                model=req.model,
                temperature=req.temperature,
            )

        try:
            patches = await service.suggest_nodes(
                text=req.text, canvas_state=req.canvas_state
            )
        except Exception as e:
            raise BuilderPlanError(f"Planning failed: {e}")
        # Last hints is declared as Dict[str, Any] on the service; guard at runtime
        lh = service.last_hints
        hints: Dict[str, Any] = lh if isinstance(lh, dict) else {}

        q_raw = hints.get("questions")
        mf_raw = hints.get("missing_fields")
        questions = q_raw if isinstance(q_raw, list) else None
        missing_fields = mf_raw if isinstance(mf_raw, dict) else None

        # Cost estimate: use token usage if present; otherwise approximate 0
        usage_obj = hints.get("usage")
        usage: Dict[str, Any] = usage_obj if isinstance(usage_obj, dict) else {}
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)

        # Try model-aware estimate if model info exists in hints
        provider_obj = hints.get("provider")
        model_obj = hints.get("model")
        provider = provider_obj if isinstance(provider_obj, str) else None
        model = model_obj if isinstance(model_obj, str) else None

        ce = CostEstimator()
        if provider or model:
            cost_estimate = ce.estimate_by_model(
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        else:
            cost_estimate = ce.estimate(
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
            ).est_usd

        return SuggestResponse(
            patches=patches,
            questions=questions,
            missing_fields=missing_fields,
            cost_estimate_usd=cost_estimate,
        )
    except BuilderPolicyViolation as e:
        # Bubble policy denials explicitly
        raise e
    except BuilderPlanError as e:
        raise e
    except Exception as e:
        raise BuilderPlanError(f"Unexpected planning error: {e}")


@router.post(
    "/propose", response_model=ProposeResponse, dependencies=[Depends(rate_limit)]
)
async def propose(
    req: ProposeRequest, service: BuilderService = Depends(_svc)
) -> ProposeResponse:
    bp = await service.propose_blueprint(text=req.text, base=req.base)
    return ProposeResponse(blueprint=bp)


@router.post("/apply", response_model=ApplyResponse, dependencies=[Depends(rate_limit)])
async def apply(
    req: ApplyRequest, service: BuilderService = Depends(_svc)
) -> ApplyResponse:
    bp = await service.apply_patch(blueprint=req.blueprint, patches=req.patches)
    return ApplyResponse(blueprint=bp)


__all__ = ["router"]
