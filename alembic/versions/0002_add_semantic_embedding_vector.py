from __future__ import annotations

from typing import Sequence

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision: str = "0002_embed_vec"
down_revision: str | None = "0001_initial_core_schema"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Ensure pgvector extension exists (no-op on SQLite)
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")  # type: ignore[arg-type]
    except Exception:
        pass

    # Add embedding vector column with common OpenAI small embedding dimension (1536)
    try:
        op.execute(
            "ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS embedding vector(1536)"
        )  # type: ignore[arg-type]
    except Exception:
        # If not Postgres/pgvector, ignore
        pass


def downgrade() -> None:
    try:
        op.execute("ALTER TABLE semantic_memory DROP COLUMN IF EXISTS embedding")  # type: ignore[arg-type]
    except Exception:
        pass
