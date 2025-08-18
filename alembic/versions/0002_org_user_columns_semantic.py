from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision: str = "0002_org_user"
down_revision: str | None = "0001_initial_core_schema"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    try:
        op.add_column(
            "semantic_memory", sa.Column("org_id", sa.String(length=64), nullable=True)
        )
        op.add_column(
            "semantic_memory", sa.Column("user_id", sa.String(length=64), nullable=True)
        )
    except Exception:
        pass
    try:
        op.create_index("ix_semantic_org_scope", "semantic_memory", ["org_id", "scope"])
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index("ix_semantic_org_scope", table_name="semantic_memory")
    except Exception:
        pass
    try:
        op.drop_column("semantic_memory", "user_id")
        op.drop_column("semantic_memory", "org_id")
    except Exception:
        pass
