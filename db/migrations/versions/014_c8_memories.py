"""C8 Six Memories Store — hybrid base table + typed pointer satellites.

Implements the approved WEL-70 decision:
docs/decisions/six-memories-store-structure.md

Creates the ``c8`` schema with:
- ``memory_entries`` — one append-only base table keyed by patient/thread/type,
  carrying authorship + lifecycle. ``payload`` is non-authoritative metadata only.
- ``memory_source_refs`` — typed pointers to C2/C4/C5/C6/C7/C9/C14/C15/C10/C11
  source objects (reference, never copy).
- ``pattern_memory_refs`` / ``responsibility_memory_refs`` — type-specific
  satellites with their own constraints.

Hard invariant (decision): a visible memory entry must have >=1 C5 evidence link.
The service enforces this at write time; this migration adds the structures and a
deferred trigger that physically rejects a ``visible`` derived entry with no
``evidence.evidence_links`` row of source_type='memory_entry'. RLS by patient_id.

Revision ID: 014
Revises: 013
Create Date: 2026-06-01
"""

from alembic import op

# ruff: noqa: E501

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS c8")

    op.execute(
        """
        CREATE TABLE c8.memory_entries (
          memory_entry_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          patient_id uuid NOT NULL,
          thread_id uuid NOT NULL,
          memory_type text NOT NULL CHECK (memory_type IN (
            'story','clinical','pattern','decision','responsibility','equity_access')),
          authorship_mode text NOT NULL CHECK (authorship_mode IN (
            'controller_authored','controller_confirmed','role_authored_pending_acceptance',
            'system_derived','hybrid')),
          lifecycle_state text NOT NULL DEFAULT 'draft' CHECK (lifecycle_state IN (
            'draft','visible','not_current','superseded_by_correction','projection_stale','archived')),
          title text,
          display_intent text NOT NULL DEFAULT 'memory_surface',
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          source_version_hash text,
          source_projection_version bigint NOT NULL DEFAULT 0,
          c10_gate_id uuid,
          created_by_actor jsonb NOT NULL DEFAULT '{}'::jsonb,
          accepted_by_controller_actor jsonb,
          accepted_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          visible_at timestamptz,
          superseded_at timestamptz,
          idempotency_key text NOT NULL UNIQUE,
          CHECK (jsonb_typeof(payload) = 'object')
        );
        CREATE INDEX ix_memory_entries_thread
          ON c8.memory_entries (patient_id, thread_id, memory_type, lifecycle_state);
        """
    )

    op.execute(
        """
        CREATE TABLE c8.memory_source_refs (
          memory_source_ref_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          memory_entry_id uuid NOT NULL REFERENCES c8.memory_entries(memory_entry_id) ON DELETE CASCADE,
          patient_id uuid NOT NULL,
          source_ref_id uuid NOT NULL,
          source_ref_type text NOT NULL CHECK (source_ref_type IN (
            'c2_raw_event','c4_extracted_fact','c5_evidence_link','c6_kg_node','c6_kg_edge',
            'c7_thread_transition','c9_pending_item','c14_investigation','c15_theory',
            'c15_theory_evaluation','c10_gate','c11_correction')),
          source_ref_version text,
          field_path text,
          link_role text NOT NULL CHECK (link_role IN (
            'primary','corroborating','contextual','contradicting','display_anchor')),
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX uq_memory_source_refs_dedup
          ON c8.memory_source_refs (
            memory_entry_id, source_ref_id, source_ref_type, COALESCE(field_path, ''));
        """
    )

    op.execute(
        """
        CREATE TABLE c8.pattern_memory_refs (
          memory_entry_id uuid PRIMARY KEY REFERENCES c8.memory_entries(memory_entry_id) ON DELETE CASCADE,
          patient_id uuid NOT NULL,
          min_current_score numeric,
          current_score numeric,
          current_score_asof timestamptz,
          source_theory_id uuid,
          source_evaluation_id uuid,
          c10_gate_id uuid NOT NULL,
          safety_level text NOT NULL CHECK (safety_level IN (
            'non_diagnostic_pattern','watchful_waiting','needs_clinician_review'))
        );
        """
    )

    op.execute(
        """
        CREATE TABLE c8.responsibility_memory_refs (
          memory_entry_id uuid PRIMARY KEY REFERENCES c8.memory_entries(memory_entry_id) ON DELETE CASCADE,
          patient_id uuid NOT NULL,
          pending_item_id uuid NOT NULL,
          pending_item_version bigint NOT NULL,
          responsibility_role text NOT NULL CHECK (responsibility_role IN (
            'patient','caregiver','clinician','care_team','admin','unknown'))
        );
        """
    )

    # Deferred trigger: a derived (clinical/pattern) entry cannot be 'visible'
    # without a C5 evidence link of source_type='memory_entry'. This is the DB
    # backstop to the application C5 gate (no orphan derived memory claims).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION c8.enforce_visible_has_evidence()
        RETURNS trigger AS $$
        DECLARE link_count int;
        BEGIN
          IF NEW.lifecycle_state = 'visible'
             AND NEW.memory_type IN ('clinical','pattern') THEN
            SELECT count(*) INTO link_count
            FROM evidence.evidence_links
            WHERE source_type = 'memory_entry'
              AND source_id = NEW.memory_entry_id;
            IF link_count < 1 THEN
              RAISE EXCEPTION 'C8 visible derived memory entry % has no C5 evidence link', NEW.memory_entry_id;
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE CONSTRAINT TRIGGER trg_c8_visible_has_evidence
          AFTER INSERT OR UPDATE ON c8.memory_entries
          DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION c8.enforce_visible_has_evidence();
        """
    )

    for table in (
        "memory_entries",
        "memory_source_refs",
        "pattern_memory_refs",
        "responsibility_memory_refs",
    ):
        op.execute(
            f"""
            ALTER TABLE c8.{table} ENABLE ROW LEVEL SECURITY;
            CREATE POLICY patient_isolation_{table} ON c8.{table}
              USING (patient_id::text = current_setting('app.patient_id', true))
              WITH CHECK (patient_id::text = current_setting('app.patient_id', true));
            """
        )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS c8 CASCADE")
    op.execute("DROP FUNCTION IF EXISTS c8.enforce_visible_has_evidence() CASCADE")
