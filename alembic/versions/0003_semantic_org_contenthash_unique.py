from __future__ import annotations

from typing import Sequence

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision: str = "0003_semantic_org_contenthash_unique"
down_revision: str | None = "0002_org_user"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Drop old unique constraint if exists
    try:
        op.drop_constraint(
            "uq_semantic_content_hash", "semantic_memory", type_="unique"
        )
    except Exception:
        pass
    # Create composite unique index for (org_id, content_hash)
    try:
        op.create_unique_constraint(
            "uq_semantic_org_content_hash",
            "semantic_memory",
            ["org_id", "content_hash"],
        )
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_constraint(
            "uq_semantic_org_content_hash", "semantic_memory", type_="unique"
        )
    except Exception:
        pass
    try:
        op.create_unique_constraint(
            "uq_semantic_content_hash", "semantic_memory", ["content_hash"]
        )
    except Exception:
        pass
