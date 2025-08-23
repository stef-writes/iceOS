"""add tags and user_id to components and blueprints

Revision ID: 0004_library_metadata
Revises: 0003_semantic_comp_ix
Create Date: 2025-08-22
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_library_metadata"
down_revision: str = "0003_semantic_comp_ix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Components: add user_id and tags (JSON)
    with op.batch_alter_table("components", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("tags", sa.JSON(), nullable=True))

    # Blueprints: add user_id and tags (JSON)
    with op.batch_alter_table("blueprints", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("tags", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("blueprints", schema=None) as batch_op:
        batch_op.drop_column("tags")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("components", schema=None) as batch_op:
        batch_op.drop_column("tags")
        batch_op.drop_column("user_id")
