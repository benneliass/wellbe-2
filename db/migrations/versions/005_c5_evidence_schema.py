"""C5 Evidence & Provenance schema.

Revision ID: 005
Revises: 004
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS evidence")

    op.create_table(
        "evidence_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "raw_context_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vault.raw_context_events.id"),
            nullable=False,
        ),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("link_type", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("confidence_basis", sa.Text(), nullable=False),
        sa.Column("relevance_span_start", sa.Integer(), nullable=True),
        sa.Column("relevance_span_end", sa.Integer(), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("linked_by", sa.Text(), nullable=False),
        sa.Column("correction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_evidence_confidence_range",
        ),
        sa.CheckConstraint(
            "link_type IN ('primary', 'corroborating', 'contradicting', 'contextual')",
            name="ck_evidence_link_type",
        ),
        sa.CheckConstraint(
            "source_type IN ('extracted_fact', 'health_signal', 'memory_entry', 'ai_summary', 'ai_response')",
            name="ck_evidence_source_type",
        ),
        sa.CheckConstraint(
            "confidence_basis IN ('extraction_model', 'user_confirmation', 'clinical_source', 'system_computed', 'correction_service')",
            name="ck_evidence_confidence_basis",
        ),
        sa.CheckConstraint(
            "linked_by IN ('user', 'system', 'pipeline', 'correction_service')",
            name="ck_evidence_linked_by",
        ),
        schema="evidence",
    )

    op.create_index(
        "ix_evidence_links_patient_source",
        "evidence_links",
        ["patient_id", "source_type", "source_id"],
        schema="evidence",
    )
    op.create_index(
        "ix_evidence_links_raw_event",
        "evidence_links",
        ["raw_context_event_id"],
        schema="evidence",
    )
    op.create_index(
        "ix_evidence_links_linked_at",
        "evidence_links",
        [sa.text("linked_at DESC")],
        schema="evidence",
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION evidence.check_raw_event_exists()
        RETURNS TRIGGER AS $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM vault.raw_context_events
            WHERE id = NEW.raw_context_event_id
          ) THEN
            RAISE EXCEPTION
              'no-orphan-claims violation: raw_context_event_id % does not exist in vault',
              NEW.raw_context_event_id;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE CONSTRAINT TRIGGER enforce_no_orphan_claims
          AFTER INSERT ON evidence.evidence_links
          DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION evidence.check_raw_event_exists();
    """)

    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'wellbe_evidence') THEN
            CREATE ROLE wellbe_evidence LOGIN PASSWORD 'wellbe_dev';
          END IF;
        END $$;
        GRANT USAGE ON SCHEMA evidence TO wellbe_evidence;
        GRANT USAGE ON SCHEMA vault TO wellbe_evidence;
        GRANT SELECT ON vault.raw_context_events TO wellbe_evidence;
        GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA evidence TO wellbe_evidence;
        ALTER DEFAULT PRIVILEGES IN SCHEMA evidence
            GRANT SELECT, INSERT ON TABLES TO wellbe_evidence;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS enforce_no_orphan_claims ON evidence.evidence_links")
    op.execute("DROP FUNCTION IF EXISTS evidence.check_raw_event_exists()")
    op.drop_index(
        "ix_evidence_links_linked_at",
        table_name="evidence_links",
        schema="evidence",
    )
    op.drop_index(
        "ix_evidence_links_raw_event",
        table_name="evidence_links",
        schema="evidence",
    )
    op.drop_index(
        "ix_evidence_links_patient_source",
        table_name="evidence_links",
        schema="evidence",
    )
    op.drop_table("evidence_links", schema="evidence")
    op.execute("DROP SCHEMA IF EXISTS evidence")
    op.execute("""
        REVOKE ALL ON SCHEMA evidence FROM wellbe_evidence;
    """)
