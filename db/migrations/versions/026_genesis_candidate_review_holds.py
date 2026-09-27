"""Things-noticed review holds: "ignore for now" and "remind me later".

Relevance candidate cards offer accept / reject / ignore for now / remind later
(docs/implementation/ui_vision_implementation_prompt.md). Accept (promote) and
reject (dismiss) already exist as terminal statuses. Ignore and remind-later are
*holds*, not decisions: the candidate stays ``pending`` (so the status CHECK is
unchanged) and is only kept off "Things noticed" for now.

- ``snoozed_until`` — hidden until this moment, then it reappears.
- ``ignored_at``    — hidden until the concern is seen again (a repeat mention
  advances ``last_seen_at`` past ``ignored_at``).

Both columns are nullable, so existing rows and writers are unaffected.

Revision ID: 026
Revises: 025
Create Date: 2026-09-27
"""

from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE genesis.thread_candidates "
        "ADD COLUMN IF NOT EXISTS snoozed_until timestamp, "
        "ADD COLUMN IF NOT EXISTS ignored_at timestamp"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE genesis.thread_candidates "
        "DROP COLUMN IF EXISTS ignored_at, "
        "DROP COLUMN IF EXISTS snoozed_until"
    )
