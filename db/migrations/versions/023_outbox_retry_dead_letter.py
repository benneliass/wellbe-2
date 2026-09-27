"""Outbox: bounded retries with backoff and a dead-letter state.

Failed outbox events used to stay undelivered and be retried every poll forever,
logging a traceback each time; one poison event could spam logs indefinitely.
Consumers now record ``attempts``/``last_error``, back off via
``next_attempt_at`` and park exhausted rows with ``dead_lettered_at`` (requeue
with ``scripts/ops/outbox.py``). The partial index serves the per-event_type
claim query, which only ever looks at undelivered, non-dead-lettered rows.

Revision ID: 023
Revises: 022
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None

_INDEX = "ix_outbox_events_claimable"


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column("attempts", sa.Integer, nullable=False, server_default=sa.text("0")),
        schema="events",
    )
    op.add_column("outbox_events", sa.Column("last_error", sa.Text, nullable=True), schema="events")
    op.add_column(
        "outbox_events",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        schema="events",
    )
    op.add_column(
        "outbox_events",
        sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True),
        schema="events",
    )
    op.create_index(
        _INDEX,
        "outbox_events",
        ["event_type", "created_at"],
        schema="events",
        postgresql_where=sa.text("delivered_at IS NULL AND dead_lettered_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name="outbox_events", schema="events")
    op.drop_column("outbox_events", "dead_lettered_at", schema="events")
    op.drop_column("outbox_events", "next_attempt_at", schema="events")
    op.drop_column("outbox_events", "last_error", schema="events")
    op.drop_column("outbox_events", "attempts", schema="events")
