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

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError

from ice_api.dependencies import rate_limit
from ice_api.redis_client import get_redis
from ice_api.security import require_auth
from ice_core.unified_registry import registry

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


# ------------------------------- Storage helpers ----------------------------


def _workspace_key(ws_id: str) -> str:
    return f"ws:{ws_id}"


def _project_key(pr_id: str) -> str:
    return f"pr:{pr_id}"


def _mounts_key(pr_id: str) -> str:
    return f"pr:{pr_id}:mounts"


def _project_blueprints_key(pr_id: str) -> str:
    return f"pr:{pr_id}:blueprints"


async def _save_json(key: str, value: BaseModel, request: Request) -> None:
    try:
        redis = get_redis()
        await redis.set(key, value.model_dump_json())  # type: ignore[misc]
        return
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    store[key] = value.model_dump(mode="json")
    request.app.state._kv = store  # type: ignore[attr-defined]


async def _load_json(model: type[BaseModel], key: str, request: Request) -> BaseModel:
    try:
        redis = get_redis()
        raw = await redis.get(key)  # type: ignore[misc]
        if raw:
            return model.model_validate_json(raw)
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    if key not in store:
        raise KeyError(key)
    return model.model_validate(store[key])


async def _list_prefix(
    model: type[BaseModel], prefix: str, request: Request
) -> List[BaseModel]:
    items: List[BaseModel] = []
    try:
        redis = get_redis()
        keys = [k async for k in redis.scan_iter(f"{prefix}*")]  # type: ignore[misc]
        for k in keys:
            raw = await redis.get(k)  # type: ignore[misc]
            if raw:
                items.append(model.model_validate_json(raw))
        return items
    except Exception:
        pass
    store: Dict[str, Any] = getattr(request.app.state, "_kv", {})
    for k, v in store.items():
        if isinstance(k, str) and k.startswith(prefix):
            items.append(model.model_validate(v))
    return items


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
    await _save_json(_workspace_key(payload.id), payload, request)
    return payload


@router.get(
    "/workspaces",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=List[Workspace],
)
async def list_workspaces(request: Request) -> List[Workspace]:  # noqa: D401
    rows = await _list_prefix(Workspace, "ws:", request)
    return [Workspace.model_validate(w.model_dump()) for w in rows]


@router.post(
    "/projects",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=Project,
)
async def create_project(request: Request, payload: Project = Body(...)) -> Project:  # noqa: D401
    # Ensure workspace exists
    try:
        await _load_json(Workspace, _workspace_key(payload.workspace_id), request)
    except Exception:
        raise HTTPException(status_code=404, detail="workspace not found")
    await _save_json(_project_key(payload.id), payload, request)
    return payload


@router.get(
    "/workspaces/{ws_id}/projects",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=List[Project],
)
async def list_projects(request: Request, ws_id: str) -> List[Project]:  # noqa: D401
    projs = [
        Project.model_validate(p.model_dump())
        for p in await _list_prefix(Project, "pr:", request)
    ]
    return [p for p in projs if p.workspace_id == ws_id]


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
    # Ensure project exists
    try:
        pr = await _load_json(Project, _project_key(project_id), request)
    except Exception:
        raise HTTPException(status_code=404, detail="project not found")
    mount = Mount(
        id=payload.id,
        project_id=pr.id,
        label=payload.label,
        uri=payload.uri,
        metadata=payload.metadata,
    )
    await _save_json(f"{_mounts_key(project_id)}:{mount.id}", mount, request)
    return mount


@router.get(
    "/projects/{project_id}/mounts",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=List[Mount],
)
async def list_mounts(request: Request, project_id: str) -> List[Mount]:  # noqa: D401
    try:
        await _load_json(Project, _project_key(project_id), request)
    except Exception:
        raise HTTPException(status_code=404, detail="project not found")
    rows = await _list_prefix(Mount, f"{_mounts_key(project_id)}:", request)
    return [Mount.model_validate(m.model_dump()) for m in rows]


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
    try:
        pr: Project = await _load_json(Project, _project_key(project_id), request)  # type: ignore[assignment]
    except Exception:
        raise HTTPException(status_code=404, detail="project not found")
    pr.enabled_tools = list(sorted(set(payload.enabled_tools)))
    pr.enabled_workflows = list(sorted(set(payload.enabled_workflows)))
    await _save_json(_project_key(project_id), pr, request)
    return pr


@router.get(
    "/projects/{project_id}/catalog",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=CatalogResponse,
)
async def get_catalog(request: Request, project_id: str) -> CatalogResponse:  # noqa: D401
    try:
        pr: Project = await _load_json(Project, _project_key(project_id), request)  # type: ignore[assignment]
    except Exception:
        raise HTTPException(status_code=404, detail="project not found")

    # Source global availability from the unified registry
    tools_all = sorted(registry.list_tools())
    workflows_all = [name for name, _ in registry.available_chains()]
    agents_all = [name for name in registry.list_agents()]

    tools = [
        CatalogEntry(name=n, type="tool", enabled=n in pr.enabled_tools)
        for n in tools_all
    ]
    workflows = [
        CatalogEntry(name=n, type="workflow", enabled=n in pr.enabled_workflows)
        for n in workflows_all
    ]
    agents = [CatalogEntry(name=n, type="agent", enabled=True) for n in agents_all]
    return CatalogResponse(tools=tools, workflows=workflows, agents=agents)


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
    try:
        await _save_json(_workspace_key(ws.id), ws, request)
    except Exception:
        pass
    try:
        # Ensure workspace exists prior to project
        await _load_json(Workspace, _workspace_key(ws.id), request)
    except Exception:
        await _save_json(_workspace_key(ws.id), ws, request)
    try:
        await _save_json(_project_key(pr.id), pr, request)
    except Exception:
        pass
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


@router.get(
    "/projects/{project_id}/blueprints",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
    response_model=ProjectBlueprintsList,
)
async def list_project_blueprints(
    request: Request, project_id: str
) -> ProjectBlueprintsList:  # noqa: D401
    """List blueprint identifiers associated with the project."""
    try:
        await _load_json(Project, _project_key(project_id), request)
    except Exception:
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
    # Ensure project exists
    try:
        await _load_json(Project, _project_key(project_id), request)
    except Exception:
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
