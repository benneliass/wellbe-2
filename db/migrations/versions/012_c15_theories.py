"""C15 Theory aggregate schema.

Implements the approved WEL-129 decision:
docs/decisions/theory-object-evaluation-and-safety.md

Creates the ``c15`` schema with:
- ``theories`` — first-class aggregate; status (personal-data finding) and
  safety_level (what C10 does with output) are SEPARATE fields; neither is a
  diagnosis (G1).
- ``theory_evaluations`` — immutable, versioned evaluation snapshots, each with
  the C10 gate result.
- ``theory_external_context`` — external sources attached as context only;
  ``context_only`` is CHECK-pinned TRUE (G2).

Hard constraints: G1 (no diagnostic statuses), G2 (external = context only),
G6 (RLS by patient_id).

Revision ID: 012
Revises: 011
Create Date: 2026-06-01
"""

from alembic import op

# ruff: noqa: E501

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS c15")

    op.execute(
        """
        CREATE TABLE c15.theories (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          patient_id uuid NOT NULL,
          created_by_actor_id uuid,
          linked_investigation_id uuid REFERENCES c14.investigations(id) ON DELETE SET NULL,
          theory_text text NOT NULL,
          normalized_question text,
          theory_type text NOT NULL CHECK (theory_type IN (
            'symptom_cause','treatment_effect','trigger','pattern','other'
          )),
          status text NOT NULL DEFAULT 'unreviewed' CHECK (status IN (
            'unreviewed','needs_more_data','partially_supported',
            'not_supported_by_current_data','contradicted_by_current_data',
            'discuss_with_clinician','clinician_reviewed'
          )),
          safety_level text NOT NULL DEFAULT 'low' CHECK (safety_level IN (
            'low','needs_clinician_context','urgent_symptom_present','blocked_due_to_diagnostic_claim'
          )),
          latest_evaluation_id uuid,
          projection_node_id uuid,
          supersedes_theory_id uuid REFERENCES c15.theories(id),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_theories_patient ON c15.theories (patient_id, status);
        CREATE INDEX ix_theories_investigation ON c15.theories (linked_investigation_id);
        """
    )

    op.execute(
        """
        CREATE TABLE c15.theory_evaluations (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          theory_id uuid NOT NULL REFERENCES c15.theories(id) ON DELETE CASCADE,
          patient_id uuid NOT NULL,
          evaluation_version integer NOT NULL CHECK (evaluation_version >= 1),
          evidence_for_node_ids uuid[] NOT NULL DEFAULT '{}',
          evidence_against_node_ids uuid[] NOT NULL DEFAULT '{}',
          missing_data jsonb NOT NULL DEFAULT '[]'::jsonb,
          external_context_link_ids uuid[] NOT NULL DEFAULT '{}',
          proposed_status text NOT NULL,
          proposed_safety_level text NOT NULL,
          c10_gate_result jsonb NOT NULL DEFAULT '{}'::jsonb,
          evaluator_actor_id uuid,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (theory_id, evaluation_version)
        );
        CREATE INDEX ix_theory_evaluations_theory ON c15.theory_evaluations (theory_id, evaluation_version);
        """
    )

    op.execute(
        """
        CREATE TABLE c15.theory_external_context (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          theory_id uuid NOT NULL REFERENCES c15.theories(id) ON DELETE CASCADE,
          patient_id uuid NOT NULL,
          external_source_id uuid NOT NULL,
          external_claim_id uuid,
          relevance_link_id uuid NOT NULL,
          context_direction text NOT NULL CHECK (context_direction IN (
            'supporting_plausibility','contradicting_plausibility','neutral'
          )),
          context_only boolean NOT NULL DEFAULT true CHECK (context_only IS TRUE),
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_theory_external_context_theory ON c15.theory_external_context (theory_id);
        """
    )

    for table in ("theories", "theory_evaluations", "theory_external_context"):
        op.execute(
            f"""
            ALTER TABLE c15.{table} ENABLE ROW LEVEL SECURITY;
            CREATE POLICY patient_isolation_{table} ON c15.{table}
              USING (patient_id::text = current_setting('app.patient_id', true))
              WITH CHECK (patient_id::text = current_setting('app.patient_id', true));
            """
        )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS c15 CASCADE")
