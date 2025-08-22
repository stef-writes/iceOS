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
            where_parts = ["scope = :scope", "key LIKE :prefix"]
            params: Dict[str, Any] = {
                "scope": scope,
                "prefix": prefix + "%",
                "limit": limit,
            }
            if org_id is not None:
                where_parts.append("org_id = :org_id")
                params["org_id"] = org_id

            sql = f"""
                SELECT key, meta_json, created_at
                FROM semantic_memory
                WHERE {' AND '.join(where_parts)}
                ORDER BY created_at DESC
                LIMIT :limit
            """
            stmt = text(sql).bindparams(
                bindparam("scope", type_=sa.String()),
                bindparam("prefix", type_=sa.String()),
                bindparam("limit", type_=sa.Integer()),
            )
            if org_id is not None:
                stmt = stmt.bindparams(bindparam("org_id", type_=sa.String()))
            rows = await session.execute(stmt, params)
            for r in rows.mappings():
                rec = dict(r)
                created = rec.get("created_at")
                try:
                    if created is not None:
                        rec["created_at"] = (
                            created.isoformat()
                        )  # ensure JSON-serializable
                except Exception:
                    pass
                items.append(rec)
        return {"items": items}


def create_recent_session_tool(**kwargs: Any) -> RecentSessionTool:
    return RecentSessionTool(**kwargs)
