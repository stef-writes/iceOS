from __future__ import annotations

"""Copilot Actions API – structured planning/validation for Canvas.

This module exposes a contract-first, structured interface that the UI can
consume without parsing free-text. It builds on top of the Builder service
and the existing Meta endpoints.

Routes
------
- POST /api/v1/copilot/suggest_v2  → structured actions, costs, hints
- POST /api/v1/copilot/validate    → dry validation of actions against a blueprint
- POST /api/v1/copilot/simulate    → apply patches in-memory and return the result
- POST /api/v1/copilot/run_plan    → lightweight run plan (graph or selection)

Design
------
- Pure Pydantic request/response models; strictly typed enums
- No side effects; simulation does not persist server-side state
- Minimal, meaningful validation with clear errors
"""

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ice_api.api.blueprints import _calculate_version_lock
from ice_api.dependencies import rate_limit
from ice_api.security import require_auth
from ice_builder.factory import create_builder_service
from ice_builder.service import BuilderService
from ice_builder.toolkit.cost_estimator import CostEstimator
from ice_core.models.mcp import PartialBlueprint
from ice_core.protocols.builder import NodePatch

router = APIRouter(
    prefix="/api/v1/copilot",
    tags=["copilot", "builder"],
    dependencies=[Depends(require_auth)],
)


class ActionKind(str):
    ADD_NODE = "add_node"
    EDIT_NODE = "edit_node"
    LINK = "link"
    RUN = "run"
    VALIDATE = "validate"


class CopilotAction(BaseModel):
    """Single structured copilot action.

    Attributes
    ----------
    id : str
        Client-generated stable id for UI reconciliation.
    kind : Literal["add_node", "edit_node", "link", "run", "validate"]
        The action verb to render in the UI.
    target : Optional[str]
        Node id the action refers to (if applicable).
    fields_changed : List[str]
        Human-friendly list of fields this action mutates (for chips).
    patches : List[NodePatch]
        Underlying low-level patches to apply.
    confidence : float
        0..1 confidence score for ranking.
    rationale_summary : Optional[str]
        Short explanation for the user; no chain-of-thought.
    """

    id: str
    kind: Literal["add_node", "edit_node", "link", "run", "validate"]
    target: Optional[str] = None
    fields_changed: List[str] = Field(default_factory=list)
    patches: List[NodePatch] = Field(default_factory=list)
    confidence: float = 0.75
    rationale_summary: Optional[str] = None


class UiHints(BaseModel):
    jump_to_node_id: Optional[str] = None
    expand_diff: bool = False
    primary_cta: Optional[Literal["apply", "connect", "run"]] = None


class SuggestV2Request(BaseModel):
    text: str
    selection: Optional[str] = None
    canvas_state: Dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[str] = None
    blueprint_lock: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None


class SuggestV2Response(BaseModel):
    actions: List[CopilotAction]
    ui_hints: UiHints = Field(default_factory=UiHints)
    costs: Dict[str, Any] = Field(default_factory=dict)
    risks: Dict[str, Any] = Field(default_factory=dict)


class ValidateRequest(BaseModel):
    blueprint: PartialBlueprint
    actions: List[CopilotAction]


class Violation(BaseModel):
    code: str
    message: str
    node_id: Optional[str] = None


class ValidateResponse(BaseModel):
    ok: bool
    violations: List[Violation] = Field(default_factory=list)
    autofixes: List[NodePatch] = Field(default_factory=list)


class SimulateRequest(BaseModel):
    blueprint: PartialBlueprint
    patches: List[NodePatch]


class SimulateResponse(BaseModel):
    blueprint: PartialBlueprint


class RunPlanRequest(BaseModel):
    blueprint: PartialBlueprint
    selection: Optional[str] = None


class RunPlanResponse(BaseModel):
    scope: Literal["graph", "selection"]
    expected_nodes: List[str] = Field(default_factory=list)
    budget_check: Optional[Dict[str, Any]] = None


def _svc() -> BuilderService:
    return create_builder_service()


def _patches_to_actions(patches: List[NodePatch]) -> List[CopilotAction]:
    actions: List[CopilotAction] = []
    for idx, p in enumerate(patches):
        # Heuristics: infer action based on path and operation
        path = getattr(p, "path", "") or ""
        op = getattr(p, "op", "replace") or "replace"
        node_id = None
        fields: List[str] = []
        # Typical paths: /nodes/{i}/type, /nodes/{i}/dependencies, /nodes/- (add)
        parts = [s for s in path.split("/") if s]
        if len(parts) >= 2 and parts[0] == "nodes":
            # If index present we can't map id directly; still capture field
            field = parts[-1]
            fields.append(field)
        # Infer kind
        if parts[:2] == ["nodes", "-"] or op == "add":
            kind = ActionKind.ADD_NODE
        elif "dependencies" in parts:
            kind = ActionKind.LINK
        else:
            kind = ActionKind.EDIT_NODE
        actions.append(
            CopilotAction(
                id=f"a{idx}",
                kind=kind,  # type: ignore[arg-type]
                target=node_id,
                fields_changed=fields,
                patches=[p],
                confidence=0.75,
                rationale_summary=None,
            )
        )
    return actions


@router.post(
    "/suggest_v2", response_model=SuggestV2Response, dependencies=[Depends(rate_limit)]
)
async def suggest_v2(req: SuggestV2Request) -> SuggestV2Response:
    """Return structured actions for the Copilot panel.

    Parameters
    ----------
    req : SuggestV2Request
        User query and canvas context.

    Returns
    -------
    SuggestV2Response
        Structured actions with costs and UI hints.
    """

    service = _svc()
    # Apply model overrides through the same policy path used by legacy suggest
    if req.provider or req.model or req.temperature is not None:
        req.canvas_state = service.apply_policy_overrides(
            task="builder/suggest_v2",
            canvas_state=req.canvas_state,
            provider=req.provider,
            model=req.model,
            temperature=req.temperature,
        )

    patches = await service.suggest_nodes(text=req.text, canvas_state=req.canvas_state)

    # Costs from hints if available
    base_hints: Dict[str, Any] = (
        service.last_hints if isinstance(service.last_hints, dict) else {}
    )
    hints: Dict[str, Any] = dict(base_hints)
    _usage_obj = hints.get("usage")
    usage: Dict[str, Any] = dict(_usage_obj) if isinstance(_usage_obj, dict) else {}
    ce = CostEstimator()
    est = ce.estimate(
        prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
        completion_tokens=int(usage.get("completion_tokens", 0) or 0),
    )

    actions = _patches_to_actions(patches)
    # Heuristic link-hints enrichment: surface a link action for dependency patches
    for idx, p in enumerate(patches):
        path = getattr(p, "path", "") or ""
        if "/dependencies" in path:
            actions.append(
                CopilotAction(
                    id=f"lh{idx}",
                    kind=ActionKind.LINK,  # type: ignore[arg-type]
                    target=None,
                    fields_changed=["dependencies"],
                    patches=[p],
                    confidence=0.8,
                    rationale_summary="Connect nodes as suggested",
                )
            )
    ui_hints = UiHints(
        jump_to_node_id=req.selection,
        expand_diff=False,
        primary_cta="apply" if actions else None,
    )
    costs = {
        "estimate_usd": est.est_usd,
        "tokens_in": est.prompt_tokens,
        "tokens_out": est.completion_tokens,
    }
    risks: Dict[str, Any] = {"stale_lock": False}
    return SuggestV2Response(
        actions=actions, ui_hints=ui_hints, costs=costs, risks=risks
    )


@router.post(
    "/validate", response_model=ValidateResponse, dependencies=[Depends(rate_limit)]
)
async def validate(req: ValidateRequest) -> ValidateResponse:  # noqa: D401
    """Validate actions against a blueprint.

    Simple checks for now:
    - At least one action
    - No more than one ADD_NODE per request (keeps UI simple)
    """

    violations: List[Violation] = []
    add_count = sum(1 for a in req.actions if a.kind == ActionKind.ADD_NODE)
    if not req.actions:
        violations.append(Violation(code="empty", message="No actions to validate"))
    if add_count > 1:
        violations.append(
            Violation(code="too_many_adds", message="Only one node addition at a time")
        )

    # Structural checks: unique ids, existing deps, no self-deps
    try:
        nodes = list(req.blueprint.nodes or [])  # type: ignore[attr-defined]
        ids = [str(getattr(n, "id")) for n in nodes]
        if len(ids) != len(set(ids)):
            violations.append(
                Violation(code="dup_id", message="Duplicate node id in blueprint")
            )
        idset = set(ids)
        for n in nodes:
            for d in list(getattr(n, "dependencies", []) or []):
                if str(d) not in idset:
                    violations.append(
                        Violation(
                            code="missing_dep",
                            message=f"Dependency '{d}' not found",
                            node_id=str(getattr(n, "id")),
                        )
                    )
        for n in nodes:
            if str(getattr(n, "id")) in list(getattr(n, "dependencies", []) or []):
                violations.append(
                    Violation(
                        code="self_dep",
                        message="Node depends on itself",
                        node_id=str(getattr(n, "id")),
                    )
                )

        # Ports/cardinality: simple policy
        # - condition: at most 1 incoming, exactly 2 outgoing (true/false) – best effort
        # - loop: at most 1 incoming; parallel: many allowed
        # - default: many in/out
        # We primarily check incoming multiplicity here.
        incoming: dict[str, int] = {nid: 0 for nid in idset}
        for n in nodes:
            for d in list(getattr(n, "dependencies", []) or []):
                if str(d) in incoming:
                    incoming[str(d)] += 1
        for n in nodes:
            nid = str(getattr(n, "id"))
            ntype = str(getattr(n, "type", ""))
            inc = incoming.get(nid, 0)
            if ntype == "condition" and inc > 1:
                violations.append(
                    Violation(
                        code="ports_in_one",
                        message="condition allows only one incoming edge",
                        node_id=nid,
                    )
                )
            if ntype == "loop" and inc > 1:
                violations.append(
                    Violation(
                        code="ports_in_one",
                        message="loop allows only one incoming edge",
                        node_id=nid,
                    )
                )
            # parallel/recursive: allow many; default: allow many
    except Exception:
        pass

    return ValidateResponse(
        ok=len(violations) == 0, violations=violations, autofixes=[]
    )


@router.post(
    "/simulate", response_model=SimulateResponse, dependencies=[Depends(rate_limit)]
)
async def simulate(req: SimulateRequest, request: Request) -> SimulateResponse:  # noqa: D401
    """Apply patches in-memory and return the resulting blueprint.

    This uses the Builder service's `apply_patch` without persisting state.
    """

    # Enforce optimistic version-lock header against body hash
    try:
        expected = _calculate_version_lock(req.blueprint)
        client_lock = request.headers.get("X-Version-Lock")
        if client_lock is None:
            raise HTTPException(status_code=428, detail="Missing X-Version-Lock header")
        if client_lock != expected:
            raise HTTPException(status_code=409, detail="Blueprint version conflict")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400, detail="Invalid blueprint for version lock"
        )

    service = _svc()
    out = await service.apply_patch(blueprint=req.blueprint, patches=req.patches)
    return SimulateResponse(blueprint=out)


@router.post(
    "/run_plan", response_model=RunPlanResponse, dependencies=[Depends(rate_limit)]
)
async def run_plan(req: RunPlanRequest) -> RunPlanResponse:  # noqa: D401
    """Produce a minimal run plan for the current blueprint/selection."""

    nodes = list(req.blueprint.nodes or [])  # type: ignore[attr-defined]
    if req.selection:
        # Collect selected node and its dependencies
        deps_of: Dict[str, List[str]] = {}
        for n in nodes:
            deps_of[str(n.id)] = list(getattr(n, "dependencies", []) or [])  # type: ignore[index]
        include: set[str] = set()
        stack = [str(req.selection)]
        while stack:
            cur = stack.pop()
            if cur in include:
                continue
            include.add(cur)
            for d in deps_of.get(cur, []):
                stack.append(str(d))
        expected = [str(n.id) for n in nodes if str(getattr(n, "id")) in include]
        scope: Literal["graph", "selection"] = "selection"
    else:
        expected = [str(getattr(n, "id")) for n in nodes]
        scope = "graph"
    return RunPlanResponse(scope=scope, expected_nodes=expected, budget_check=None)


__all__ = ["router"]
