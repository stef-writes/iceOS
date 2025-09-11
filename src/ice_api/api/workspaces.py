"""Workspace / Project / Mounts / Catalog APIs.

MVP storage model
-----------------
- Primary persistence remains Postgres for Blueprints; for project scaffolding
  we use Redis with in-memory fallback (same pattern used by blueprint helpers).

Contract (stable shape)
-----------------------
- Workspace: {id: str, name: str}
- Project: {id: str, workspace_id: str, name: str, enabled_tools: list[str], enabled_workflows: list[str]}
- Mount: {id: str, project_id: str, label: str, uri: str, metadata: dict}

Notes
- Identity injection (org/user/session) is handled in execution/tool routes; this
  module focuses on scoping lists for Studio (palette + assets).
"""

from typing import Any, Dict, List, Optional
import sqlalchemy as sa
from ice_api.redis_client import get_redis

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, ValidationError

from ice_api.dependencies import rate_limit
from ice_api.security import require_auth
from ice_core.unified_registry import registry
from ice_api.db.database_session_async import get_session
from ice_api.db.orm_models_core import (
    WorkspaceRecord,
    ProjectRecord,
    MountRecord,
)

# Import helpers from blueprints API to validate existence and compute version locks
from .blueprints import _calculate_version_lock as _bp_version_lock
from .blueprints import _load_blueprint as _load_blueprint_by_id  # type: ignore
from .templates import FromWorkflowRequest

router = APIRouter(prefix="/api/v1", tags=["workspaces", "projects", "catalog"])


# ------------------------------- Models -------------------------------------


class Workspace(BaseModel):
    id: str
    name: str


class Project(BaseModel):
    id: str
    workspace_id: str
    name: str
    enabled_tools: List[str] = Field(default_factory=list)
    enabled_workflows: List[str] = Field(default_factory=list)


class Mount(BaseModel):
    id: str
    project_id: str
    label: str
    uri: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CatalogEntry(BaseModel):
    name: str
    type: str  # tool | workflow | agent
    enabled: bool


class CatalogResponse(BaseModel):
    tools: List[CatalogEntry]
    workflows: List[CatalogEntry]
    agents: List[CatalogEntry]


class BootstrapResponse(BaseModel):
    workspace_id: str
    project_id: str


# ------------------------------- Assoc helpers (transient) -------------------


def _project_blueprints_key(pr_id: str) -> str:
    # Kept in Redis for sidebar ordering/history only (non-authoritative)
    return f"pr:{pr_id}:blueprints"


# ------------------------------- Routes -------------------------------------


@router.post(
    "/workspaces",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=Workspace,
)
async def create_workspace(
    request: Request, payload: Workspace = Body(...)
) -> Workspace:  # noqa: D401
    async for session in get_session():
        rec = await session.get(WorkspaceRecord, payload.id)
        if rec is None:
            rec = WorkspaceRecord(id=payload.id, name=payload.name)
            session.add(rec)
        else:
            rec.name = payload.name
        await session.commit()
    return payload


@router.get(
    "/workspaces",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=List[Workspace],
)
async def list_workspaces(request: Request) -> List[Workspace]:  # noqa: D401
    items: List[Workspace] = []
    async for session in get_session():
        rows = (await session.execute(
            sa.select(WorkspaceRecord)  # type: ignore[name-defined]
        )).scalars().all()
        for r in rows:
            items.append(Workspace(id=r.id, name=r.name))
    return items


@router.post(
    "/projects",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=Project,
)
async def create_project(request: Request, payload: Project = Body(...)) -> Project:  # noqa: D401
    async for session in get_session():
        ws = await session.get(WorkspaceRecord, payload.workspace_id)
        if ws is None:
            raise HTTPException(status_code=404, detail="workspace not found")
        rec = await session.get(ProjectRecord, payload.id)
        if rec is None:
            rec = ProjectRecord(
                id=payload.id,
                workspace_id=payload.workspace_id,
                name=payload.name,
                enabled_tools=payload.enabled_tools,
                enabled_workflows=payload.enabled_workflows,
            )
            session.add(rec)
        else:
            rec.name = payload.name
            rec.enabled_tools = payload.enabled_tools
            rec.enabled_workflows = payload.enabled_workflows
        await session.commit()
    return payload


@router.get(
    "/workspaces/{ws_id}/projects",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=List[Project],
)
async def list_projects(request: Request, ws_id: str) -> List[Project]:  # noqa: D401
    items: List[Project] = []
    async for session in get_session():
        rows = (await session.execute(
            sa.select(ProjectRecord).where(ProjectRecord.workspace_id == ws_id)  # type: ignore[name-defined]
        )).scalars().all()
        for r in rows:
            items.append(
                Project(
                    id=r.id,
                    workspace_id=r.workspace_id,
                    name=r.name,
                    enabled_tools=r.enabled_tools or [],
                    enabled_workflows=r.enabled_workflows or [],
                )
            )
    return items


class MountCreate(BaseModel):
    id: str
    label: str
    uri: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post(
    "/projects/{project_id}/mounts",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=Mount,
)
async def add_mount(
    request: Request, project_id: str, payload: MountCreate = Body(...)
) -> Mount:  # noqa: D401
    async for session in get_session():
        pr = await session.get(ProjectRecord, project_id)
        if pr is None:
            raise HTTPException(status_code=404, detail="project not found")
        rec = await session.get(MountRecord, payload.id)
        if rec is None:
            rec = MountRecord(
                id=payload.id,
                project_id=project_id,
                label=payload.label,
                uri=payload.uri,
                meta_json=payload.metadata,
            )
            session.add(rec)
        else:
            rec.label = payload.label
            rec.uri = payload.uri
            rec.meta_json = payload.metadata
        await session.commit()
    return Mount(id=payload.id, project_id=project_id, label=payload.label, uri=payload.uri, metadata=payload.metadata)


@router.get(
    "/projects/{project_id}/mounts",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=List[Mount],
)
async def list_mounts(request: Request, project_id: str) -> List[Mount]:  # noqa: D401
    items: List[Mount] = []
    async for session in get_session():
        pr = await session.get(ProjectRecord, project_id)
        if pr is None:
            raise HTTPException(status_code=404, detail="project not found")
        rows = (await session.execute(
            sa.select(MountRecord).where(MountRecord.project_id == project_id)
        )).scalars().all()
        for r in rows:
            items.append(
                Mount(
                    id=r.id,
                    project_id=r.project_id,
                    label=r.label,
                    uri=r.uri,
                    metadata=r.meta_json or {},
                )
            )
    return items


class CatalogUpdate(BaseModel):
    enabled_tools: List[str] = Field(default_factory=list)
    enabled_workflows: List[str] = Field(default_factory=list)


@router.put(
    "/projects/{project_id}/catalog",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=Project,
)
async def update_catalog(
    request: Request, project_id: str, payload: CatalogUpdate = Body(...)
) -> Project:  # noqa: D401
    async for session in get_session():
        rec = await session.get(ProjectRecord, project_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="project not found")
        rec.enabled_tools = list(sorted(set(payload.enabled_tools)))
        rec.enabled_workflows = list(sorted(set(payload.enabled_workflows)))
        await session.commit()
        return Project(
            id=rec.id,
            workspace_id=rec.workspace_id,
            name=rec.name,
            enabled_tools=rec.enabled_tools or [],
            enabled_workflows=rec.enabled_workflows or [],
        )
    # Defensive fallback if session generator yielded nothing
    raise HTTPException(status_code=500, detail="database session unavailable")


@router.get(
    "/projects/{project_id}/catalog",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=CatalogResponse,
)
async def get_catalog(request: Request, project_id: str) -> CatalogResponse:  # noqa: D401
    async for session in get_session():
        rec = await session.get(ProjectRecord, project_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="project not found")

        # Source global availability from the unified registry
        tools_all = sorted(registry.list_tools())
        workflows_all = [name for name, _ in registry.available_chains()]
        agents_all = [name for name in registry.list_agents()]

        tools = [
            CatalogEntry(name=n, type="tool", enabled=n in (rec.enabled_tools or []))
            for n in tools_all
        ]
        workflows = [
            CatalogEntry(name=n, type="workflow", enabled=n in (rec.enabled_workflows or []))
            for n in workflows_all
        ]
        agents = [CatalogEntry(name=n, type="agent", enabled=True) for n in agents_all]
        return CatalogResponse(tools=tools, workflows=workflows, agents=agents)
    # Defensive fallback if session generator yielded nothing
    return CatalogResponse(tools=[], workflows=[], agents=[])


@router.post(
    "/bootstrap",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=BootstrapResponse,
)
async def bootstrap_defaults(request: Request) -> BootstrapResponse:  # noqa: D401
    """Ensure a default workspace and project exist; return their ids.

    Idempotent and zero-setup friendly.
    """
    ws = Workspace(id="default", name="Default Workspace")
    pr = Project(id="default", workspace_id=ws.id, name="Default Project")
    async for session in get_session():
        w = await session.get(WorkspaceRecord, ws.id)
        if w is None:
            session.add(WorkspaceRecord(id=ws.id, name=ws.name))
        p = await session.get(ProjectRecord, pr.id)
        if p is None:
            session.add(
                ProjectRecord(
                    id=pr.id,
                    workspace_id=pr.workspace_id,
                    name=pr.name,
                    enabled_tools=[],
                    enabled_workflows=[],
                )
            )
        await session.commit()
    return BootstrapResponse(workspace_id=ws.id, project_id=pr.id)


# ------------------------------- Project blueprints ---------------------------


class ProjectBlueprintsList(BaseModel):
    blueprint_ids: List[str]


class ProjectBlueprintAddResponse(BaseModel):
    id: str
    version_lock: str


async def _append_project_blueprint(
    project_id: str, blueprint_id: str, request: Request
) -> None:
    try:
        redis = get_redis()
        # Keep a simple list for ordering/history
        await redis.rpush(_project_blueprints_key(project_id), blueprint_id)  # type: ignore[misc]
        return
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    key = _project_blueprints_key(project_id)
    ids: List[str] = store.get(key, []) if isinstance(store.get(key), list) else []
    ids.append(blueprint_id)
    store[key] = ids
    request.app.state._kv = store  # type: ignore[attr-defined]


async def _list_project_blueprint_ids(project_id: str, request: Request) -> List[str]:
    try:
        redis = get_redis()
        raw = await redis.lrange(_project_blueprints_key(project_id), 0, -1)  # type: ignore[misc]
        ids: List[str] = []
        for r in raw:
            if isinstance(r, (bytes, bytearray)):
                try:
                    ids.append(r.decode())
                except Exception:
                    continue
            elif isinstance(r, str):
                ids.append(r)
        return ids
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    key = _project_blueprints_key(project_id)
    if isinstance(store.get(key), list):
        return [str(x) for x in store.get(key, [])]
    return []


async def _remove_project_blueprint(
    project_id: str, blueprint_id: str, request: Request
) -> None:
    """Remove a blueprint id from a project's list (best-effort)."""
    # Redis first
    try:
        redis = get_redis()
        # Remove all occurrences
        await redis.lrem(_project_blueprints_key(project_id), 0, blueprint_id)  # type: ignore[misc]
        return
    except Exception:
        pass
    # In-memory fallback
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    key = _project_blueprints_key(project_id)
    ids: List[str] = store.get(key, []) if isinstance(store.get(key), list) else []
    store[key] = [i for i in ids if str(i) != str(blueprint_id)]
    request.app.state._kv = store  # type: ignore[attr-defined]


@router.get(
    "/projects/{project_id}/blueprints",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=ProjectBlueprintsList,
)
async def list_project_blueprints(
    request: Request, project_id: str
) -> ProjectBlueprintsList:  # noqa: D401
    """List blueprint identifiers associated with the project."""
    # Ensure project exists in DB
    async for session in get_session():
        pr = await session.get(ProjectRecord, project_id)
        if pr is None:
            raise HTTPException(status_code=404, detail="project not found")
    return ProjectBlueprintsList(
        blueprint_ids=await _list_project_blueprint_ids(project_id, request)
    )


@router.post(
    "/projects/{project_id}/blueprints/from-workflow",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=ProjectBlueprintAddResponse,
)
async def create_project_blueprint_from_workflow(  # noqa: D401
    request: Request,
    project_id: str,
    payload: FromWorkflowRequest = Body(...),
) -> ProjectBlueprintAddResponse:
    """Materialize a template into a stored Blueprint and associate with project.

    This aliases the Templates API, then records the blueprint id into the project's
    blueprint listing for sidebar/navigation UX.
    """
    # Ensure project exists in DB
    async for session in get_session():
        pr = await session.get(ProjectRecord, project_id)
        if pr is None:
            raise HTTPException(status_code=404, detail="project not found")

    # Delegate to Templates logic for YAML → Blueprint → persistence
    import yaml as _yaml  # lazy import

    from ice_core.models.mcp import Blueprint as _Blueprint  # type: ignore

    from .templates import (  # type: ignore
        _calculate_version_lock,
        _find_workflow_yaml,
        _persist_blueprint_to_store,
    )

    wf_path = _find_workflow_yaml(payload.workflow_id, payload.path_hint)
    try:
        data = _yaml.safe_load(wf_path.read_text(encoding="utf-8")) or {}
        nodes = data.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("Invalid template: missing nodes")
        # Best-effort bundle extraction from path
        bundle_name: Optional[str] = None
        try:
            parts = list(wf_path.parts)
            if "bundles" in parts:
                idx = parts.index("bundles")
                if idx + 1 < len(parts):
                    bundle_name = parts[idx + 1]
        except Exception:
            bundle_name = None
        blueprint_dict: Dict[str, Any] = {
            "schema_version": str(data.get("schema_version", "1.2.0")),
            "metadata": {
                "workflow": payload.workflow_id,
                "project_id": project_id,
                **({"bundle": bundle_name} if bundle_name else {}),
            },
            "nodes": nodes,
        }
        bp = _Blueprint.model_validate(blueprint_dict)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except Exception as exc:  # pragma: no cover – defensive
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    new_id = await _persist_blueprint_to_store(bp, request)
    await _append_project_blueprint(project_id, new_id, request)
    version_lock = _calculate_version_lock(bp)
    return ProjectBlueprintAddResponse(id=new_id, version_lock=version_lock)


# ------------------------------- Project attach existing blueprint -----------


class ProjectBlueprintAttachRequest(BaseModel):
    """Request payload to attach an existing workflow (blueprint) to a project.

    Args:
        blueprint_id (str): Identifier of an existing blueprint.

    Returns:
        None

    Example:
        POST /api/v1/projects/{id}/blueprints/attach with body {"blueprint_id": "..."}
    """

    blueprint_id: str


@router.post(
    "/projects/{project_id}/blueprints/attach",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=ProjectBlueprintAddResponse,
)
async def attach_project_blueprint(  # noqa: D401
    request: Request,
    project_id: str,
    payload: ProjectBlueprintAttachRequest,
) -> ProjectBlueprintAddResponse:
    """Attach an existing workflow to the project's workflow list.

    Validates that the project exists and the blueprint id resolves; then records
    the blueprint id into the project's blueprint listing (for navigation/UX).
    """
    # Ensure project exists in DB
    async for session in get_session():
        pr = await session.get(ProjectRecord, project_id)
        if pr is None:
            raise HTTPException(status_code=404, detail="project not found")

    # Validate blueprint exists and compute its current version lock
    try:
        bp = await _load_blueprint_by_id(payload.blueprint_id)
    except HTTPException:
        raise HTTPException(status_code=404, detail="blueprint not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    await _append_project_blueprint(project_id, payload.blueprint_id, request)
    return ProjectBlueprintAddResponse(
        id=payload.blueprint_id, version_lock=_bp_version_lock(bp)
    )


@router.delete(
    "/projects/{project_id}/blueprints/{blueprint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def detach_project_blueprint(  # noqa: D401
    request: Request,
    project_id: str,
    blueprint_id: str,
) -> Response:
    """Detach a workflow (blueprint id) from the project’s workflow list."""
    # Ensure project exists in DB (404 if missing)
    async for session in get_session():
        pr = await session.get(ProjectRecord, project_id)
        if pr is None:
            raise HTTPException(status_code=404, detail="project not found")
    await _remove_project_blueprint(project_id, blueprint_id, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
