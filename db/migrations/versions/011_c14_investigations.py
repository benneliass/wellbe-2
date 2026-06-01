"""C14 Investigation aggregate schema.

Implements the approved WEL-128 decision:
docs/decisions/investigation-object-and-thread-coupling.md

Creates the ``c14`` schema with:
- ``investigations`` — first-class aggregate with its own workflow lifecycle
- ``investigation_threads`` — many-to-many link to C7 threads (primary/secondary/related)
- ``investigation_participants`` — participants existing only under C1/C17 grants
- ``investigation_allowed_transitions`` — seeded workflow edges (parity with the
  Python matrix in wellbe_contracts.c14_investigation)
- a BEFORE UPDATE trigger enforcing edge validity + version monotonicity

Hard constraints honoured:
- G1: status values are workflow state only (no diagnosed/ruled_out/confirmed)
- G6: rows are patient-scoped with RLS via app.patient_id (defence-in-depth;
  the app role owns the tables and bypasses RLS, restricted roles do not)
- closure is gated by C7 in the C14 service layer, not the schema

Revision ID: 011
Revises: 010
Create Date: 2026-06-01
"""

from alembic import op

# ruff: noqa: E501

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None

_ALLOWED_EDGES = [
    ("open", "monitoring"),
    ("open", "waiting_for_data"),
    ("open", "ready_for_visit"),
    ("open", "handed_off"),
    ("open", "closed"),
    ("monitoring", "open"),
    ("monitoring", "waiting_for_data"),
    ("monitoring", "ready_for_visit"),
    ("monitoring", "handed_off"),
    ("monitoring", "closed"),
    ("waiting_for_data", "open"),
    ("waiting_for_data", "monitoring"),
    ("waiting_for_data", "ready_for_visit"),
    ("waiting_for_data", "handed_off"),
    ("waiting_for_data", "closed"),
    ("ready_for_visit", "open"),
    ("ready_for_visit", "monitoring"),
    ("ready_for_visit", "waiting_for_data"),
    ("ready_for_visit", "handed_off"),
    ("ready_for_visit", "closed"),
    ("handed_off", "monitoring"),
    ("handed_off", "closed"),
    ("closed", "open"),
]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS c14")

    op.execute(
        """
        CREATE TABLE c14.investigations (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          patient_id uuid NOT NULL,
          primary_question text NOT NULL,
          status text NOT NULL DEFAULT 'open' CHECK (status IN (
            'open','monitoring','waiting_for_data','ready_for_visit','handed_off','closed'
          )),
          status_version integer NOT NULL DEFAULT 1 CHECK (status_version >= 1),
          status_reason text,
          owner_type text NOT NULL CHECK (owner_type IN ('user','caregiver','system')),
          owner_grant_id uuid,
          scope jsonb NOT NULL DEFAULT '{}'::jsonb,
          evidence_bundle_ids uuid[] NOT NULL DEFAULT '{}',
          active_theory_ids uuid[] NOT NULL DEFAULT '{}',
          pending_item_ids uuid[] NOT NULL DEFAULT '{}',
          missing_context_items jsonb NOT NULL DEFAULT '[]'::jsonb,
          safety_flags jsonb NOT NULL DEFAULT '[]'::jsonb,
          outputs jsonb NOT NULL DEFAULT '{}'::jsonb,
          projection_node_id uuid,
          last_reviewed_at timestamptz,
          next_review_at timestamptz,
          created_by_actor_id uuid,
          created_under_grant_id uuid,
          status_changed_at timestamptz NOT NULL DEFAULT now(),
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_investigations_patient ON c14.investigations (patient_id, status);
        """
    )

    op.execute(
        """
        CREATE TABLE c14.investigation_threads (
          investigation_id uuid NOT NULL REFERENCES c14.investigations(id) ON DELETE CASCADE,
          thread_id uuid NOT NULL,
          patient_id uuid NOT NULL,
          relationship text NOT NULL DEFAULT 'primary'
            CHECK (relationship IN ('primary','secondary','related')),
          linked_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (investigation_id, thread_id)
        );
        CREATE INDEX ix_investigation_threads_thread ON c14.investigation_threads (thread_id);
        """
    )

    op.execute(
        """
        CREATE TABLE c14.investigation_participants (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          investigation_id uuid NOT NULL REFERENCES c14.investigations(id) ON DELETE CASCADE,
          patient_id uuid NOT NULL,
          actor_id uuid NOT NULL,
          role text NOT NULL,
          grant_id uuid NOT NULL,
          status text NOT NULL DEFAULT 'active'
            CHECK (status IN ('active','revoked','expired')),
          added_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (investigation_id, actor_id, role)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE c14.investigation_state_transitions (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          investigation_id uuid NOT NULL REFERENCES c14.investigations(id) ON DELETE CASCADE,
          patient_id uuid NOT NULL,
          from_status text NOT NULL,
          to_status text NOT NULL,
          transition_seq integer NOT NULL,
          reason_code text NOT NULL,
          actor_id uuid,
          idempotency_key text NOT NULL,
          correlation_id text NOT NULL,
          event_id uuid,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (investigation_id, transition_seq),
          UNIQUE (investigation_id, idempotency_key)
        );
        CREATE INDEX ix_investigation_transitions ON c14.investigation_state_transitions (investigation_id, transition_seq);
        """
    )

    op.execute(
        """
        CREATE TABLE c14.investigation_allowed_transitions (
          from_status text NOT NULL,
          to_status text NOT NULL,
          PRIMARY KEY (from_status, to_status)
        );
        """
    )
    values_sql = ", ".join(f"('{f}', '{t}')" for f, t in _ALLOWED_EDGES)
    op.execute(
        f"""
        INSERT INTO c14.investigation_allowed_transitions (from_status, to_status)
        VALUES {values_sql}
        ON CONFLICT (from_status, to_status) DO NOTHING;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION c14.enforce_investigation_transition()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.status IS DISTINCT FROM OLD.status THEN
                IF NOT EXISTS (
                    SELECT 1 FROM c14.investigation_allowed_transitions a
                    WHERE a.from_status = OLD.status AND a.to_status = NEW.status
                ) THEN
                    RAISE EXCEPTION
                        'Illegal investigation transition: % -> %', OLD.status, NEW.status
                        USING ERRCODE = 'check_violation';
                END IF;
                IF NEW.status_version <= OLD.status_version THEN
                    RAISE EXCEPTION
                        'investigation status_version must increase (% -> %)',
                        OLD.status_version, NEW.status_version
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_enforce_investigation_transition
            BEFORE UPDATE ON c14.investigations
            FOR EACH ROW
            EXECUTE FUNCTION c14.enforce_investigation_transition();
        """
    )

    # RLS (defence-in-depth; mirrors external_bridge.relevance_links pattern).
    for table in (
        "investigations",
        "investigation_threads",
        "investigation_participants",
        "investigation_state_transitions",
    ):
        op.execute(
            f"""
            ALTER TABLE c14.{table} ENABLE ROW LEVEL SECURITY;
            CREATE POLICY patient_isolation_{table} ON c14.{table}
              USING (patient_id::text = current_setting('app.patient_id', true))
              WITH CHECK (patient_id::text = current_setting('app.patient_id', true));
            """
        )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_enforce_investigation_transition ON c14.investigations"
    )
    op.execute("DROP FUNCTION IF EXISTS c14.enforce_investigation_transition()")
    op.execute("DROP SCHEMA IF EXISTS c14 CASCADE")
