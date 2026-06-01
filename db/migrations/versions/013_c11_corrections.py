"""C11 Correction Service schema — append-only, source-linked overlays.

Implements the approved WEL-71 decision:
docs/decisions/correction-service-layered-provenance.md

Creates the ``c11`` schema with:
- ``corrections`` — append-only overlay records (never mutate targets); status
  controls participation in resolved reads.
- ``correction_targets`` — what each correction points at (kind/id/field_path)
  with semantic rank.
- ``correction_resolution_events`` — append-only log of resolution changes.
- ``applied_correction_candidates_v`` — applied-only candidates with authority
  rank, consumed by the shared resolver.

Hard invariants (decision): C11 never updates/deletes targets; corrections carry
C2 provenance (raw_correction_event_id) and attach to targets via C5 links with
correction_id set (created by the service through the C5 repository). RLS by
patient_id (G6).

Revision ID: 013
Revises: 012
Create Date: 2026-06-01
"""

from alembic import op

# ruff: noqa: E501

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS c11")

    op.execute(
        """
        CREATE TABLE c11.corrections (
          correction_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          patient_id uuid NOT NULL,
          status text NOT NULL CHECK (status IN (
            'draft','pending_controller_acceptance','applied','superseded','rejected','withdrawn'
          )),
          correction_type text NOT NULL CHECK (correction_type IN (
            'replace_value','mark_incorrect','add_missing_context','mark_stale',
            'withdraw_from_current_view','relabel_thread','merge_duplicate',
            'split_context','change_evidence_weight'
          )),
          actor_authority text NOT NULL CHECK (actor_authority IN (
            'controller','controller_accepted_proposal','delegated_controller',
            'role_proposed','system_suggested'
          )),
          actor_ref jsonb NOT NULL DEFAULT '{}'::jsonb,
          grant_id uuid,
          role_binding_id uuid,
          raw_correction_event_id uuid NOT NULL,
          rationale text,
          proposed_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          accepted_by_controller_actor jsonb,
          accepted_at timestamptz,
          applied_at timestamptz,
          effective_at timestamptz,
          supersedes_correction_id uuid REFERENCES c11.corrections(correction_id),
          created_at timestamptz NOT NULL DEFAULT now(),
          idempotency_key text NOT NULL UNIQUE,
          CHECK (jsonb_typeof(proposed_payload) = 'object'),
          CHECK (
            (status = 'pending_controller_acceptance' AND actor_authority IN ('role_proposed','system_suggested'))
            OR status <> 'pending_controller_acceptance'
          )
        );
        CREATE INDEX ix_corrections_patient ON c11.corrections (patient_id, status);
        """
    )

    op.execute(
        """
        CREATE TABLE c11.correction_targets (
          correction_target_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          correction_id uuid NOT NULL REFERENCES c11.corrections(correction_id) ON DELETE CASCADE,
          patient_id uuid NOT NULL,
          target_kind text NOT NULL CHECK (target_kind IN (
            'c2_raw_event','c4_extracted_fact','c5_evidence_link','c6_kg_node','c6_kg_edge',
            'c7_thread_label','c8_memory_entry','c9_pending_item','c14_investigation','c15_theory'
          )),
          target_id uuid NOT NULL,
          target_version text,
          field_path text,
          base_value_hash text,
          proposed_value_hash text,
          semantic_rank smallint NOT NULL DEFAULT 50,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX uq_correction_targets_dedup
          ON c11.correction_targets (correction_id, target_kind, target_id, COALESCE(field_path, ''));
        CREATE INDEX ix_correction_targets_target
          ON c11.correction_targets (patient_id, target_kind, target_id, COALESCE(field_path, ''));
        """
    )

    op.execute(
        """
        CREATE TABLE c11.correction_resolution_events (
          resolution_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          correction_id uuid NOT NULL REFERENCES c11.corrections(correction_id),
          patient_id uuid NOT NULL,
          target_kind text NOT NULL,
          target_id uuid NOT NULL,
          field_path text,
          resolution_action text NOT NULL CHECK (resolution_action IN (
            'became_active','superseded_prior','lost_precedence','removed_from_current_view',
            'rejected_pending','withdrawn_by_controller'
          )),
          prior_active_correction_id uuid,
          new_active_correction_id uuid,
          occurred_at timestamptz NOT NULL DEFAULT now(),
          idempotency_key text NOT NULL UNIQUE
        );
        """
    )

    # Applied-only candidates with precomputed authority rank for the resolver.
    op.execute(
        """
        CREATE VIEW c11.applied_correction_candidates_v AS
        SELECT
          c.patient_id,
          ct.target_kind,
          ct.target_id,
          ct.field_path,
          c.correction_id,
          c.correction_type,
          c.actor_authority,
          CASE c.actor_authority
            WHEN 'controller' THEN 100
            WHEN 'controller_accepted_proposal' THEN 90
            WHEN 'delegated_controller' THEN 80
            WHEN 'role_proposed' THEN 20
            WHEN 'system_suggested' THEN 10
          END AS authority_rank,
          ct.semantic_rank,
          c.effective_at,
          c.applied_at,
          c.supersedes_correction_id,
          c.proposed_payload
        FROM c11.corrections c
        JOIN c11.correction_targets ct ON ct.correction_id = c.correction_id
        WHERE c.status = 'applied';
        """
    )

    for table in ("corrections", "correction_targets", "correction_resolution_events"):
        op.execute(
            f"""
            ALTER TABLE c11.{table} ENABLE ROW LEVEL SECURITY;
            CREATE POLICY patient_isolation_{table} ON c11.{table}
              USING (patient_id::text = current_setting('app.patient_id', true))
              WITH CHECK (patient_id::text = current_setting('app.patient_id', true));
            """
        )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS c11.applied_correction_candidates_v")
    op.execute("DROP SCHEMA IF EXISTS c11 CASCADE")
