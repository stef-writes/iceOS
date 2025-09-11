"""add workspaces projects mounts

Revision ID: 0005_add_workspaces_projects_mounts
Revises: 0004_library_metadata
Create Date: 2025-09-11 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0005_add_workspaces_projects_mounts"
down_revision = "0004_library_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:  # noqa: D401
    """Create workspaces, projects, mounts tables."""
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.String(length=64), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled_tools", sa.JSON(), nullable=True),
        sa.Column("enabled_workflows", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_projects_workspace_id", "projects", ["workspace_id"])

    op.create_table(
        "mounts",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(length=64), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("uri", sa.String(length=1024), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_mounts_project_id", "mounts", ["project_id"])


def downgrade() -> None:  # noqa: D401
    """Drop workspaces, projects, mounts tables."""
    op.drop_index("ix_mounts_project_id", table_name="mounts")
    op.drop_table("mounts")
    op.drop_index("ix_projects_workspace_id", table_name="projects")
    op.drop_table("projects")
    op.drop_table("workspaces")


