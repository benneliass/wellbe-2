"""C9 time-aware pending items + C12 in-app notifications.

1. Backfill: active result/referral waiting items created before C9 set due dates
   get ``due_at = created_at + window`` (result 7 days, referral 28 days — the
   defaults in ``wellbe_c9_continuity.policy``), ``due_precision =
   relative_policy`` and status ``scheduled`` so the due/overdue sweeper picks
   them up. Only items still open with no due date are touched. Items whose
   window already lapsed become due/overdue on the first sweep; the backfill
   itself emits no events, so no "new follow-up" notifications are produced.
2. ``notifications.in_app_notifications``: in-app reminders derived from
   ``c9.pending_item.created/.due/.overdue`` (owner decision: in-app only).
   ``idempotency_key`` is unique so a replayed event cannot duplicate a row.

Revision ID: 024
Revises: 023
Create Date: 2026-09-27
"""

from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute(
        """
        UPDATE c9.pending_items
           SET due_at = created_at + CASE item_type
                 WHEN 'result_pending' THEN interval '7 days'
                 WHEN 'referral_pending' THEN interval '28 days'
               END,
               due_precision = 'relative_policy',
               status = 'scheduled',
               version = version + 1,
               updated_at = now()
         WHERE due_at IS NULL
           AND item_type IN ('result_pending', 'referral_pending')
           AND status = 'active'
        """
    )

    op.execute("CREATE SCHEMA IF NOT EXISTS notifications")
    op.execute(
        """
        CREATE TABLE notifications.in_app_notifications (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          patient_id uuid NOT NULL,
          kind text NOT NULL CHECK (kind IN (
            'pending_item_created','pending_item_due','pending_item_overdue')),
          title text NOT NULL,
          body text NOT NULL,
          pending_item_id uuid REFERENCES c9.pending_items(pending_item_id) ON DELETE CASCADE,
          thread_id uuid,
          source_event_id uuid,
          idempotency_key text NOT NULL UNIQUE,
          created_at timestamptz NOT NULL DEFAULT now(),
          read_at timestamptz
        );
        CREATE INDEX ix_in_app_notifications_patient
          ON notifications.in_app_notifications (patient_id, created_at DESC);
        CREATE INDEX ix_in_app_notifications_unread
          ON notifications.in_app_notifications (patient_id) WHERE read_at IS NULL;
        ALTER TABLE notifications.in_app_notifications ENABLE ROW LEVEL SECURITY;
        CREATE POLICY patient_isolation_in_app_notifications
          ON notifications.in_app_notifications
          USING (patient_id::text = current_setting('app.patient_id', true))
          WITH CHECK (patient_id::text = current_setting('app.patient_id', true));
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS notifications CASCADE")
    # Open policy-dated items (scheduled, due or overdue) go back to open-ended
    # active items with no due date; settled items keep their history.
    op.execute(
        """
        UPDATE c9.pending_items
           SET due_at = NULL,
               due_precision = 'unknown',
               status = 'active',
               version = version + 1,
               updated_at = now()
         WHERE due_precision = 'relative_policy'
           AND item_type IN ('result_pending', 'referral_pending')
           AND status IN ('scheduled', 'due', 'overdue')
        """
    )
