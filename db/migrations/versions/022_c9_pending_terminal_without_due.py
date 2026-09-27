"""C9 pending items: allow terminal statuses without a due date.

The ledger CHECK required ``due_at`` for every status outside
draft/active/waiting_external/no_due_date, which also covered the terminal
statuses. An open-ended item (e.g. "Waiting for a result" with no known date)
could therefore never be resolved, cancelled or superseded: C9's reconciliation
failed with a CheckViolation and the item stayed active forever. Timer statuses
(scheduled/due/overdue/in_progress) still require a due date.

Revision ID: 022
Revises: 021
Create Date: 2026-09-27
"""

from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None

_OPEN_ENDED = "'draft','active','waiting_external','no_due_date'"
_TERMINAL = "'result_received','resolved','cancelled','superseded'"


def upgrade() -> None:
    op.execute("ALTER TABLE c9.pending_items DROP CONSTRAINT pending_items_check")
    op.execute(
        "ALTER TABLE c9.pending_items ADD CONSTRAINT pending_items_check "
        f"CHECK ((due_at IS NOT NULL) OR (status IN ({_OPEN_ENDED},{_TERMINAL})))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE c9.pending_items DROP CONSTRAINT pending_items_check")
    op.execute(
        "ALTER TABLE c9.pending_items ADD CONSTRAINT pending_items_check "
        f"CHECK ((due_at IS NOT NULL) OR (status IN ({_OPEN_ENDED})))"
    )
