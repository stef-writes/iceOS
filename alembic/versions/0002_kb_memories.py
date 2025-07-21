from __future__ import annotations

"""knowledge base & memory tables

Revision ID: 0002_kb_memories
Revises: 0001_initial
Create Date: 2025-07-13
"""


revision = "0002_kb_memories"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Delegated to automatic create_all in dev/test; production will autogenerate.
    pass


def downgrade() -> None:
    pass
