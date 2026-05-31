"""C4 Processing Pipeline schema.

Revision ID: 004
Revises: 003
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS processing")

    op.create_table(
        "extracted_facts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "raw_context_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vault.raw_context_events.id"),
            nullable=False,
        ),
        sa.Column("fact_type", sa.Text(), nullable=False),
        sa.Column("entity_label", sa.Text(), nullable=False),
        sa.Column("normalized_key", sa.Text(), nullable=False),
        sa.Column("code_system", sa.Text(), nullable=True),
        sa.Column("code", sa.Text(), nullable=True),
        sa.Column("text_span_start", sa.Integer(), nullable=True),
        sa.Column("text_span_end", sa.Integer(), nullable=True),
        sa.Column("source_text_excerpt_hash", sa.Text(), nullable=True),
        sa.Column("extraction_confidence", sa.Float(), nullable=False),
        sa.Column("extraction_model", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("pipeline_version", sa.Text(), nullable=False),
        sa.Column("quality_flag", sa.Text(), nullable=False),
        sa.Column(
            "quality_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=True,
        ),
        sa.Column("is_negated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_historical", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_hypothetical", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("subject", sa.Text(), nullable=False, server_default="patient"),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "extraction_confidence >= 0 AND extraction_confidence <= 1",
            name="ck_fact_confidence_range",
        ),
        sa.CheckConstraint(
            "quality_flag IN ('clean', 'low_confidence', 'requires_review', 'partial')",
            name="ck_fact_quality_flag",
        ),
        sa.CheckConstraint(
            "subject IN ('patient', 'family_member', 'other')",
            name="ck_fact_subject",
        ),
        schema="processing",
    )

    op.create_index(
        "ix_extracted_facts_patient_type",
        "extracted_facts",
        ["patient_id", "fact_type"],
        schema="processing",
    )
    op.create_index(
        "ix_extracted_facts_patient_extracted",
        "extracted_facts",
        ["patient_id", sa.text("extracted_at DESC")],
        schema="processing",
    )
    op.create_index(
        "ix_extracted_facts_raw_event",
        "extracted_facts",
        ["raw_context_event_id"],
        schema="processing",
    )

    op.create_table(
        "health_signals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "raw_context_event_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("signal_value", sa.Float(), nullable=False),
        sa.Column("signal_unit", sa.Text(), nullable=True),
        sa.Column("signal_direction", sa.Text(), nullable=True),
        sa.Column("aggregation_method", sa.Text(), nullable=True),
        sa.Column("observation_window", sa.Text(), nullable=True),
        sa.Column("extraction_confidence", sa.Float(), nullable=False),
        sa.Column("extraction_model", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("pipeline_version", sa.Text(), nullable=False),
        sa.Column("quality_flag", sa.Text(), nullable=False),
        sa.Column(
            "quality_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=True,
        ),
        sa.Column("captured_at_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "extraction_confidence >= 0 AND extraction_confidence <= 1",
            name="ck_signal_confidence_range",
        ),
        sa.CheckConstraint(
            "quality_flag IN ('clean', 'low_confidence', 'requires_review', 'partial')",
            name="ck_signal_quality_flag",
        ),
        schema="processing",
    )

    op.create_index(
        "ix_health_signals_patient_type",
        "health_signals",
        ["patient_id", "signal_type"],
        schema="processing",
    )
    op.create_index(
        "ix_health_signals_patient_extracted",
        "health_signals",
        ["patient_id", sa.text("extracted_at DESC")],
        schema="processing",
    )

    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'wellbe_processing') THEN
            CREATE ROLE wellbe_processing LOGIN PASSWORD 'wellbe_dev';
          END IF;
        END $$;
        GRANT USAGE ON SCHEMA processing TO wellbe_processing;
        GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA processing TO wellbe_processing;
        ALTER DEFAULT PRIVILEGES IN SCHEMA processing
            GRANT SELECT, INSERT ON TABLES TO wellbe_processing;
    """)


def downgrade() -> None:
    op.drop_index(
        "ix_health_signals_patient_extracted",
        table_name="health_signals",
        schema="processing",
    )
    op.drop_index(
        "ix_health_signals_patient_type",
        table_name="health_signals",
        schema="processing",
    )
    op.drop_table("health_signals", schema="processing")
    op.drop_index(
        "ix_extracted_facts_raw_event",
        table_name="extracted_facts",
        schema="processing",
    )
    op.drop_index(
        "ix_extracted_facts_patient_extracted",
        table_name="extracted_facts",
        schema="processing",
    )
    op.drop_index(
        "ix_extracted_facts_patient_type",
        table_name="extracted_facts",
        schema="processing",
    )
    op.drop_table("extracted_facts", schema="processing")
    op.execute("DROP SCHEMA IF EXISTS processing")
    op.execute("""
        REVOKE ALL ON SCHEMA processing FROM wellbe_processing;
    """)
