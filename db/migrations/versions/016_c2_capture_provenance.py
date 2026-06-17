"""C2 ingest provenance — rich W3C-PROV/FHIR-Provenance-aligned record per raw event.

Implements the approved capture-write-path decision:
docs/decisions/capture-write-path-contract.md (Q3 = A3b "rich provenance record").

Adds ``vault.raw_context_provenance``: one append-only provenance row per
``vault.raw_context_events`` row, modelling the ingest as a W3C-PROV
entity/activity/agent triple (the raw artifact entity, the ``ingest`` activity,
the user actor + software agent) plus occurred/recorded times, correlation id,
and the sha-256 content hash. C5 "no orphan claims" source-linking reads this.

The capture write path (WEL-155) reuses the existing ``manual_text`` and ``pdf``
source types, carrying the product-level ``capture_type`` in ``source_metadata``;
no new source-type seeds are required.

RLS by patient_id; UPDATE/DELETE rejected (append-only, like the events table).

Revision ID: 016
Revises: 015
Create Date: 2026-06-18
"""

from alembic import op

# ruff: noqa: E501

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE vault.raw_context_provenance (
          provenance_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          event_id uuid NOT NULL UNIQUE REFERENCES vault.raw_context_events(id),
          patient_id uuid NOT NULL,
          -- W3C PROV: entity (the raw artifact), activity, agent(s)
          entity_kind text NOT NULL DEFAULT 'raw_context_event',
          activity text NOT NULL DEFAULT 'ingest',
          agent_actor_id uuid NOT NULL,
          agent_software text NOT NULL,
          agent_software_version text NOT NULL,
          capture_type text,
          content_hash text NOT NULL,
          occurred_at timestamp NOT NULL,
          recorded_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
          correlation_id text NOT NULL,
          trace_id text,
          created_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
        )
        """
    )

    op.execute(
        "CREATE INDEX ix_raw_context_provenance_patient ON vault.raw_context_provenance (patient_id)"
    )

    op.execute(
        """
        GRANT SELECT, INSERT ON vault.raw_context_provenance TO wellbe_vault;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_raw_context_provenance_immutable
          BEFORE UPDATE OR DELETE ON vault.raw_context_provenance
          FOR EACH ROW EXECUTE FUNCTION vault.reject_mutation();
        """
    )

    op.execute(
        """
        ALTER TABLE vault.raw_context_provenance ENABLE ROW LEVEL SECURITY;

        CREATE POLICY patient_isolation ON vault.raw_context_provenance
          USING (patient_id::text = current_setting('app.patient_id', true));
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS patient_isolation ON vault.raw_context_provenance")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_raw_context_provenance_immutable ON vault.raw_context_provenance"
    )
    op.execute("DROP INDEX IF EXISTS vault.ix_raw_context_provenance_patient")
    op.execute("DROP TABLE IF EXISTS vault.raw_context_provenance")
