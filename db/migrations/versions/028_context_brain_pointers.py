"""Raw Context Brain pointer graph and exploration sessions.

The vault remains the only copy of note text. These tables keep graph pointers,
the accepted projection, and the server-held exploration session.

Revision ID: 028
Revises: 027
Create Date: 2026-10-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS context_brain")
    op.create_table(
        "graph_snapshot",
        sa.Column("person_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="context_brain",
    )
    op.create_table(
        "exploration_session",
        sa.Column("token", sa.Text(), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="context_brain",
    )
    op.create_index(
        "exploration_session_person",
        "exploration_session",
        ["person_id"],
        schema="context_brain",
    )


def downgrade() -> None:
    op.drop_index("exploration_session_person", table_name="exploration_session", schema="context_brain")
    op.drop_table("exploration_session", schema="context_brain")
    op.drop_table("graph_snapshot", schema="context_brain")
    op.execute("DROP SCHEMA IF EXISTS context_brain")
