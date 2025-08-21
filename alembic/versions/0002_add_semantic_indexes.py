from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision: str = "0002_add_semantic_indexes"
down_revision: str | None = "0001_initial_core_schema"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Composite index to speed exact lookups and per-user listings
    op.create_index(
        "ix_semantic_org_user_key",
        "semantic_memory",
        ["org_id", "user_id", "key"],
    )
    # Cover ordered listings by scope/org with recent-first
    op.create_index(
        "ix_semantic_scope_org_created",
        "semantic_memory",
        ["scope", "org_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_semantic_scope_org_created", table_name="semantic_memory")
    op.drop_index("ix_semantic_org_user_key", table_name="semantic_memory")
