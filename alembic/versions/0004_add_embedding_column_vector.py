from __future__ import annotations

from typing import Sequence

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision: str = "0004_add_embedding_column_vector"
down_revision: str | None = "0003_semantic_org_contenthash_unique"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Ensure pgvector extension exists
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")  # type: ignore[arg-type]
    except Exception:
        pass

    # Add embedding column if it's missing (idempotent)
    op.execute(
        "ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS embedding vector(1536)"
    )  # type: ignore[arg-type]

    # Optional: create a vector index for faster ANN search (idempotent)
    # Note: requires PostgreSQL with pgvector installed
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_semantic_embedding_cosine "
        "ON semantic_memory USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)"
    )  # type: ignore[arg-type]


def downgrade() -> None:
    # Keep embedding column and index in place to avoid data loss; no-op downgrade.
    pass
