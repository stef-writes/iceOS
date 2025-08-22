from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision: str = "0003_add_semantic_memory_composite_indexes"
down_revision: str | None = "0002_add_semantic_indexes"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Composite index to accelerate per-user key lookups in the library flow
    op.create_index(
        "ix_semantic_org_user_key",
        "semantic_memory",
        ["org_id", "user_id", "key"],
    )

    # Composite index to accelerate scoped, recent listings (created_at DESC)
    # Note: Not all databases support DESC index ordering; Postgres does.
    try:
        op.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_semantic_scope_org_created_at ON semantic_memory (scope, org_id, created_at DESC)"
            )
        )
    except Exception:
        # Fallback for engines that do not support IF NOT EXISTS
        op.create_index(
            "ix_semantic_scope_org_created_at",
            "semantic_memory",
            ["scope", "org_id", "created_at"],
        )


def downgrade() -> None:
    try:
        op.drop_index("ix_semantic_scope_org_created_at", table_name="semantic_memory")
    except Exception:
        # If the IF NOT EXISTS path created a different variant, attempt the known name
        pass
    op.drop_index("ix_semantic_org_user_key", table_name="semantic_memory")
