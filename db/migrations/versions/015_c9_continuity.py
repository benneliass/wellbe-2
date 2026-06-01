"""C9 Continuity & Closure Engine — pending item ledger + timer bookkeeping.

Implements the approved WEL-67 decision:
docs/decisions/continuity-pending-ledger-durable-timers.md

Creates the ``c9`` schema with:
- ``pending_items`` — operational source of truth for continuity (never clinical
  facts or thread state). Carries timer_epoch + last-observed thread context for
  stale-command protection, and the normal-test safety-net flags.
- ``pending_item_thread_links`` — many-to-thread links.
- ``pending_item_events`` — append-only per-item event log.
- ``consumed_thread_events`` — dedupe ledger for thread.state_changed (event_id PK,
  unique (thread_id, transition_seq)).
- ``timer_actions`` — append-only timer outcome log; unique per (item, epoch,
  action) makes activity retries idempotent.

RLS by patient_id on patient-scoped tables.

Revision ID: 015
Revises: 014
Create Date: 2026-06-01
"""

from alembic import op

# ruff: noqa: E501

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS c9")

    op.execute(
        """
        CREATE TABLE c9.pending_items (
          pending_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          patient_id uuid NOT NULL,
          primary_thread_id uuid NOT NULL,
          item_type text NOT NULL CHECK (item_type IN (
            'result_pending','referral_pending','follow_up_due','repeat_test_due',
            'post_visit_plan_check','normal_test_safety_net','user_next_step','care_team_next_step')),
          status text NOT NULL CHECK (status IN (
            'draft','active','waiting_external','scheduled','due','overdue','in_progress',
            'result_received','resolved','cancelled','superseded','no_due_date')),
          title text NOT NULL,
          next_action_code text,
          due_at timestamptz,
          due_precision text NOT NULL DEFAULT 'unknown'
            CHECK (due_precision IN ('unknown','date','datetime','relative_policy')),
          owner_ref jsonb,
          contact_ref jsonb,
          source_ref jsonb NOT NULL DEFAULT '{}'::jsonb,
          evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
          investigation_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
          latest_observed_thread_transition_seq bigint,
          latest_observed_thread_status_version bigint,
          blocks_c9_closure_request boolean NOT NULL DEFAULT false,
          normal_test_safety_net boolean NOT NULL DEFAULT false,
          symptoms_persist_state text NOT NULL DEFAULT 'unknown'
            CHECK (symptoms_persist_state IN ('unknown','reported_persistent','reported_resolved','not_applicable')),
          timer_epoch bigint NOT NULL DEFAULT 0,
          workflow_id text UNIQUE,
          workflow_run_id text,
          version bigint NOT NULL DEFAULT 1,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          resolved_at timestamptz,
          cancelled_at timestamptz,
          idempotency_key text NOT NULL UNIQUE,
          CHECK ((due_at IS NOT NULL) OR (status IN ('draft','active','waiting_external','no_due_date')))
        );
        CREATE INDEX ix_pending_items_thread ON c9.pending_items (patient_id, primary_thread_id, status);
        CREATE INDEX ix_pending_items_due ON c9.pending_items (status, due_at) WHERE due_at IS NOT NULL;
        """
    )

    op.execute(
        """
        CREATE TABLE c9.pending_item_thread_links (
          pending_item_id uuid NOT NULL REFERENCES c9.pending_items(pending_item_id) ON DELETE CASCADE,
          thread_id uuid NOT NULL,
          relationship text NOT NULL CHECK (relationship IN ('primary','related','blocked_by','blocks_follow_up')),
          PRIMARY KEY (pending_item_id, thread_id, relationship)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE c9.pending_item_events (
          pending_item_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          pending_item_id uuid NOT NULL REFERENCES c9.pending_items(pending_item_id) ON DELETE CASCADE,
          patient_id uuid NOT NULL,
          event_type text NOT NULL,
          event_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          actor jsonb NOT NULL DEFAULT '{}'::jsonb,
          occurred_at timestamptz NOT NULL DEFAULT now(),
          idempotency_key text NOT NULL UNIQUE
        );
        """
    )

    op.execute(
        """
        CREATE TABLE c9.consumed_thread_events (
          event_id uuid PRIMARY KEY,
          thread_id uuid NOT NULL,
          transition_seq bigint NOT NULL,
          consumed_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (thread_id, transition_seq)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE c9.timer_actions (
          timer_action_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          pending_item_id uuid NOT NULL REFERENCES c9.pending_items(pending_item_id) ON DELETE CASCADE,
          patient_id uuid NOT NULL,
          timer_epoch bigint NOT NULL,
          action_type text NOT NULL CHECK (action_type IN (
            'started','rescheduled','cancelled','fired','c7_transition_requested',
            'c7_transition_accepted','no_op_stale','no_op_c7_rejected','failed_transient')),
          c7_transition_id uuid,
          c7_rejection_code text,
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          occurred_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (pending_item_id, timer_epoch, action_type)
        );
        """
    )

    for table in ("pending_items", "pending_item_events", "timer_actions"):
        op.execute(
            f"""
            ALTER TABLE c9.{table} ENABLE ROW LEVEL SECURITY;
            CREATE POLICY patient_isolation_{table} ON c9.{table}
              USING (patient_id::text = current_setting('app.patient_id', true))
              WITH CHECK (patient_id::text = current_setting('app.patient_id', true));
            """
        )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS c9 CASCADE")
