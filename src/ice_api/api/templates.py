"""Templates API: list Bundles and materialize a template into a Blueprint.

Exposes:
- GET /api/v1/templates: List available template workflows discovered under plugins/bundles/**/workflows/*.yaml
- POST /api/v1/templates/from-bundle: Create a Blueprint from a bundle workflow YAML and return its id

Notes
- YAML is used only for shipping built-in templates; user-authored graphs live as Blueprints in the DB.
- Identity (org/user/session) is injected server-side elsewhere; this API solely materializes design-time graphs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError

from ice_api.db.database_session_async import get_session
from ice_api.db.orm_models_core import BlueprintRecord
from ice_api.dependencies import rate_limit
from ice_api.security import require_auth
from ice_core.models.mcp import Blueprint

# Reuse internal helpers from blueprints API for consistency
from .blueprints import (  # type: ignore[F401]
    _calculate_version_lock,
    _save_blueprint,
    _validate_resolvable_and_allowed,
)

router = APIRouter(prefix="/api/v1/templates", tags=["templates", "library"])


class TemplateEntry(BaseModel):
    """Catalog entry for a template workflow.

    Args:
        id (str): Workflow id declared in YAML (e.g., "chatkit.rag_chat").
        bundle (str): Bundle directory name (e.g., "chatkit").
        path (str): Relative path to the workflow YAML within repo.
        description (str | None): Optional short description.

    Example:
        >>> TemplateEntry(id="chatkit.rag_chat", bundle="chatkit", path="plugins/bundles/chatkit/workflows/rag_chat.yaml")
    """

    id: str = Field(...)
    bundle: str = Field(...)
    path: str = Field(...)
    description: Optional[str] = Field(default=None)


class TemplatesList(BaseModel):
    templates: List[TemplateEntry]


@router.get(
    "/",
    response_model=TemplatesList,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def list_templates() -> TemplatesList:  # noqa: D401
    """Return available built-in template workflows discovered under plugins/bundles.

    Returns:
        TemplatesList: List of available templates with ids and paths.

    """

    project_root = Path(__file__).resolve().parents[3]
    bundles_root = project_root / "plugins" / "bundles"

    templates: List[TemplateEntry] = []
    if bundles_root.exists():
        for bundle_dir in sorted(p for p in bundles_root.iterdir() if p.is_dir()):
            wf_dir = bundle_dir / "workflows"
            if not wf_dir.exists():
                continue
            for wf_file in sorted(wf_dir.glob("*.yaml")):
                try:
                    data = yaml.safe_load(wf_file.read_text(encoding="utf-8")) or {}
                    wf_id = str(data.get("id", "")).strip()
                    if not wf_id:
                        continue
                    desc = None
                    # Optionally pick description from adjacent bundle.yaml if present
                    bundle_yaml = bundle_dir / "bundle.yaml"
                    if bundle_yaml.exists():
                        try:
                            by = (
                                yaml.safe_load(bundle_yaml.read_text(encoding="utf-8"))
                                or {}
                            )
                            desc = by.get("description")
                        except Exception:
                            pass
                    templates.append(
                        TemplateEntry(
                            id=wf_id,
                            bundle=bundle_dir.name,
                            path=str(wf_file.relative_to(project_root)),
                            description=desc,
                        )
                    )
                except Exception:
                    # Skip invalid YAMLs silently; they are developer-owned assets
                    continue

    return TemplatesList(templates=templates)


class FromBundleRequest(BaseModel):
    """Request to materialize a bundle workflow into a stored Blueprint.

    Args:
        bundle_id (str): Workflow id declared in YAML (e.g., "chatkit.rag_chat").
        path_hint (str | None): Optional relative path to speed up lookup.

    Example:
        >>> FromBundleRequest(bundle_id="chatkit.rag_chat")
    """

    bundle_id: str
    path_hint: Optional[str] = Field(default=None)


class FromBundleResponse(BaseModel):
    id: str
    version_lock: str


def _find_workflow_yaml(bundle_id: str, path_hint: Optional[str]) -> Path:
    project_root = Path(__file__).resolve().parents[3]
    if path_hint:
        p = (project_root / path_hint).resolve()
        if p.exists():
            return p
    # Fallback: scan bundles
    for wf in (project_root / "plugins" / "bundles").rglob("*.yaml"):
        try:
            data = yaml.safe_load(wf.read_text(encoding="utf-8")) or {}
            if str(data.get("id", "")).strip() == bundle_id:
                return wf
        except Exception:
            continue
    raise FileNotFoundError(f"Template not found for id: {bundle_id}")


async def _persist_blueprint_to_store(blueprint: Blueprint, request: Request) -> str:
    """Persist a Blueprint to Postgres (authoritative) and Redis cache; return id."""

    new_id: Optional[str] = None
    # DB authoritative
    try:
        async for session in get_session():
            rec = BlueprintRecord(
                id=str(uuid4()),  # type: ignore[name-defined]
                schema_version=str(getattr(blueprint, "schema_version", "1.2.0")),
                body=blueprint.model_dump(mode="json", exclude_none=True),
                lock_version=1,
            )
            await session.merge(rec)
            await session.commit()
            new_id = rec.id
    except Exception:
        # Fallback to in-memory app state for dev
        store = getattr(request.app.state, "blueprints", None)
        if store is not None:
            new_id = str(uuid4())  # type: ignore[name-defined]
            store[new_id] = blueprint
        else:
            new_id = str(uuid4())  # type: ignore[name-defined]
            request.app.state.blueprints = {new_id: blueprint}

    # Cache to Redis best-effort
    try:
        await _save_blueprint(new_id, blueprint)  # type: ignore[arg-type]
    except Exception:
        pass
    return str(new_id)


@router.post(
    "/from-bundle",
    response_model=FromBundleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def create_blueprint_from_bundle(  # noqa: D401
    request: Request,
    payload: FromBundleRequest = Body(...),
) -> FromBundleResponse:
    """Materialize a template into a stored Blueprint and return its id.

    Reads the workflow YAML by id, validates resolvability, persists the Blueprint,
    and returns the new identifier and version lock.
    """

    wf_path = _find_workflow_yaml(payload.bundle_id, payload.path_hint)
    try:
        data = yaml.safe_load(wf_path.read_text(encoding="utf-8")) or {}
        nodes = data.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("Invalid template: missing nodes")
        blueprint_dict: Dict[str, Any] = {
            "schema_version": str(data.get("schema_version", "1.2.0")),
            "metadata": {"bundle": payload.bundle_id},
            "nodes": nodes,
        }
        bp = Blueprint.model_validate(blueprint_dict)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except Exception as exc:  # pragma: no cover – defensive
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Enforce resolvability and access
    _validate_resolvable_and_allowed(bp)

    # Persist
    new_id = await _persist_blueprint_to_store(bp, request)

    # Cache best-effort to Redis done inside helper; compute lock
    version_lock = _calculate_version_lock(bp)
    return FromBundleResponse(id=new_id, version_lock=version_lock)


# Local imports to avoid top-level circulars
from uuid import uuid4  # noqa: E402
