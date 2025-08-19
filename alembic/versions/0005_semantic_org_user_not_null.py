from __future__ import annotations

from typing import Sequence

from alembic import op  # type: ignore

revision: str = "0005_semantic_org_user_not_null"
down_revision: str | None = "0004_add_embedding_column_vector"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Backfill NULL org_id/user_id to defaults to preserve rows
    op.execute(
        """
        UPDATE semantic_memory
        SET org_id = COALESCE(org_id, 'default'),
            user_id = COALESCE(user_id, 'system')
        WHERE org_id IS NULL OR user_id IS NULL
        """
    )
    # Enforce NOT NULL
    op.execute("ALTER TABLE semantic_memory ALTER COLUMN org_id SET NOT NULL")
    op.execute("ALTER TABLE semantic_memory ALTER COLUMN user_id SET NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE semantic_memory ALTER COLUMN user_id DROP NOT NULL")
    op.execute("ALTER TABLE semantic_memory ALTER COLUMN org_id DROP NOT NULL")
