from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision: str = "0001_initial_core_schema"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Create pgvector extension if running on Postgres
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")  # type: ignore[arg-type]
    except Exception:
        pass

    op.create_table(
        "components",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("org_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "blueprints",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.Column(
            "lock_version", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("org_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "executions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("blueprint_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cost_meta", sa.JSON(), nullable=True),
        sa.Column("org_id", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["blueprint_id"], ["blueprints.id"]),
    )
    op.create_index("ix_executions_status", "executions", ["status"])
    op.create_index("ix_executions_blueprint_id", "executions", ["blueprint_id"])

    op.create_table(
        "execution_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("execution_id", sa.String(length=64), nullable=False),
        sa.Column("node_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"]),
    )
    op.create_index(
        "ix_execution_events_execution_id", "execution_events", ["execution_id"]
    )
    op.create_index("ix_execution_events_node_id", "execution_events", ["node_id"])
    op.create_index(
        "ix_execution_events_event_type", "execution_events", ["event_type"]
    )
    op.create_index("ix_execution_events_ts", "execution_events", ["ts"])

    op.create_table(
        "tokens",
        sa.Column("token_hash", sa.String(length=255), primary_key=True),
        sa.Column("org_id", sa.String(length=64), nullable=True),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )

    op.create_table(
        "semantic_memory",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(length=128), nullable=False),
        sa.Column("key", sa.String(length=256), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        # Optional pgvector column; ignore on non-Postgres
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_semantic_scope_key", "semantic_memory", ["scope", "key"])
    op.create_unique_constraint(
        "uq_semantic_content_hash", "semantic_memory", ["content_hash"]
    )
    try:
        op.execute(
            "ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS embedding vector(1536)"
        )  # type: ignore[arg-type]
    except Exception:
        pass


def downgrade() -> None:
    op.drop_index("ix_semantic_scope_key", table_name="semantic_memory")
    op.drop_constraint("uq_semantic_content_hash", "semantic_memory", type_="unique")
    op.drop_table("semantic_memory")
    op.drop_table("tokens")
    op.drop_index("ix_execution_events_ts", table_name="execution_events")
    op.drop_index("ix_execution_events_event_type", table_name="execution_events")
    op.drop_index("ix_execution_events_node_id", table_name="execution_events")
    op.drop_index("ix_execution_events_execution_id", table_name="execution_events")
    op.drop_table("execution_events")
    op.drop_index("ix_executions_blueprint_id", table_name="executions")
    op.drop_index("ix_executions_status", table_name="executions")
    op.drop_table("executions")
    op.drop_table("blueprints")
    op.drop_table("components")
