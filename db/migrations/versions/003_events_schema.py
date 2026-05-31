"""Create events schema and outbox_events table.

Revision ID: 003
Revises: 002
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS events")

    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("correlation_id", sa.Text, nullable=False),
        sa.Column("trace_id", sa.Text, nullable=False),
        sa.Column("delivered_at", sa.DateTime, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        schema="events",
    )

    op.create_index(
        "ix_outbox_events_delivered_at",
        "outbox_events",
        ["delivered_at"],
        schema="events",
    )


def downgrade() -> None:
    op.drop_table("outbox_events", schema="events")
    op.execute("DROP SCHEMA IF EXISTS events")
