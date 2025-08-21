from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import Field

from ice_core.base_tool import ToolBase


class RecentSessionTool(ToolBase):
    name: str = "recent_session_tool"
    description: str = Field(
        "Fetch recent chat turns for a session (by key prefix chat:{session_id}:*), newest first."
    )

    async def _execute_impl(
        self,
        *,
        session_id: str,
        scope: str = "kb",
        limit: int = 5,
        org_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return recent session keys for inclusion in prompts."""
        import sqlalchemy as sa
        from sqlalchemy import bindparam, text

        from ice_api.db.database_session_async import get_session

        prefix = f"chat:{session_id}:"
        items: list[dict[str, Any]] = []
        async for session in get_session():
            stmt = text(
                """
                SELECT key, meta_json, created_at
                FROM semantic_memory
                WHERE scope = :scope
                  AND (:org_id IS NULL OR org_id = :org_id)
                  AND key LIKE :prefix
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ).bindparams(
                bindparam("scope", type_=sa.String()),
                bindparam("org_id", type_=sa.String()),
                bindparam("prefix", type_=sa.String()),
                bindparam("limit", type_=sa.Integer()),
            )
            rows = await session.execute(
                stmt,
                {
                    "scope": scope,
                    "org_id": org_id,
                    "prefix": prefix + "%",
                    "limit": limit,
                },
            )
            for r in rows.mappings():
                items.append(dict(r))
        return {"items": items}


def create_recent_session_tool(**kwargs: Any) -> RecentSessionTool:
    return RecentSessionTool(**kwargs)
