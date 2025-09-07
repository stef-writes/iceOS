from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from ice_core.base_tool import ToolBase
from ice_core.unified_registry import registry


class RepoManifestLoaderTool(ToolBase):
    name: str = "repo_manifest_loader"
    description: str = Field(
        "Scan a mounted repository path for plugins.v0 manifests and register components.",
    )

    async def _execute_impl(
        self,
        *,
        mount_path: str,
        allow_dynamic: bool = True,
    ) -> Dict[str, Any]:
        from pathlib import Path

        base = Path(mount_path)
        if not base.exists():
            return {"ok": False, "error": f"mount path not found: {mount_path}"}

        manifests: list[Path] = []
        for p in base.rglob("plugins.v0.yaml"):
            manifests.append(p)
        for p in base.rglob("plugins.v0.json"):
            manifests.append(p)

        loaded: list[str] = []
        errors: list[str] = []
        for mp in manifests:
            try:
                count = registry.load_plugins(str(mp), allow_dynamic=allow_dynamic)
                loaded.append(f"{mp} (+{count})")
            except Exception as exc:  # pragma: no cover – defensive
                errors.append(f"{mp}: {exc}")

        return {"ok": True, "loaded": loaded, "errors": errors}


def create_repo_manifest_loader(**kwargs: Any) -> RepoManifestLoaderTool:
    return RepoManifestLoaderTool(**kwargs)


registry.register_tool_factory(
    "repo_manifest_loader", __name__ + ":create_repo_manifest_loader"
)
