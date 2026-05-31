"""C2 Raw Context Vault schema.

Revision ID: 002
Revises: a1b2c3d4e5f6
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


SOURCE_TYPE_SEEDS = [
    {
        "code": "manual_text",
        "display_name": "Manual Text Entry",
        "status": "active",
        "requires_blob": False,
        "default_mime_types": ["text/plain"],
    },
    {
        "code": "photo",
        "display_name": "Photo",
        "status": "active",
        "requires_blob": True,
        "default_mime_types": ["image/jpeg", "image/png"],
    },
    {
        "code": "pdf",
        "display_name": "PDF Document",
        "status": "active",
        "requires_blob": True,
        "default_mime_types": ["application/pdf"],
    },
    {
        "code": "sms",
        "display_name": "SMS Message",
        "status": "active",
        "requires_blob": False,
        "default_mime_types": ["text/plain"],
    },
    {
        "code": "device",
        "display_name": "Wearable / IoT Device",
        "status": "active",
        "requires_blob": False,
        "default_mime_types": ["application/json"],
    },
    {
        "code": "fhir",
        "display_name": "FHIR Resource",
        "status": "active",
        "requires_blob": False,
        "default_mime_types": ["application/fhir+json"],
    },
    {
        "code": "environmental",
        "display_name": "Environmental Context",
        "status": "active",
        "requires_blob": False,
        "default_mime_types": ["application/json"],
    },
]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS vault")

    op.create_table(
        "raw_context_source_types",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default="active",
        ),
        sa.Column("requires_blob", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "default_mime_types",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
        ),
        sa.CheckConstraint("status IN ('active', 'deprecated')", name="ck_source_type_status"),
        schema="vault",
    )

    source_types_table = sa.table(
        "raw_context_source_types",
        sa.column("code", sa.Text),
        sa.column("display_name", sa.Text),
        sa.column("status", sa.Text),
        sa.column("requires_blob", sa.Boolean),
        sa.column("default_mime_types", postgresql.ARRAY(sa.Text)),
        schema="vault",
    )
    op.bulk_insert(source_types_table, SOURCE_TYPE_SEEDS)

    op.create_table(
        "raw_context_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_type",
            sa.Text(),
            sa.ForeignKey("vault.raw_context_source_types.code"),
            nullable=False,
        ),
        sa.Column("source_id", sa.Text(), nullable=True),
        sa.Column("external_source_id", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False, unique=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("hash_scope", sa.Text(), nullable=False, server_default="patient"),
        sa.Column("blob_ref", sa.Text(), nullable=True),
        sa.Column("blob_bucket", sa.Text(), nullable=True),
        sa.Column("blob_key", sa.Text(), nullable=True),
        sa.Column("blob_version_id", sa.Text(), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("encoding", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("original_filename_hash", sa.Text(), nullable=True),
        sa.Column(
            "source_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("adapter_name", sa.Text(), nullable=False),
        sa.Column("adapter_version", sa.Text(), nullable=False),
        sa.Column(
            "ingestor_version",
            sa.Text(),
            nullable=False,
            server_default="0.1.0",
        ),
        sa.Column("consent_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("share_grant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("encryption_key_id", sa.Text(), nullable=False),
        sa.Column(
            "encryption_key_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("retention_policy_id", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column(
            "duplicate_of_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vault.raw_context_events.id"),
            nullable=True,
        ),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="vault",
    )

    op.create_index(
        "ix_raw_context_events_patient_created",
        "raw_context_events",
        ["patient_id", sa.text("created_at DESC")],
        schema="vault",
    )
    op.create_index(
        "ix_raw_context_events_patient_hash",
        "raw_context_events",
        ["patient_id", "content_hash"],
        schema="vault",
    )

    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'wellbe_vault') THEN
            CREATE ROLE wellbe_vault LOGIN PASSWORD 'wellbe_dev';
          END IF;
        END $$;
        GRANT USAGE ON SCHEMA vault TO wellbe_vault;
        GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA vault TO wellbe_vault;
        ALTER DEFAULT PRIVILEGES IN SCHEMA vault
            GRANT SELECT, INSERT ON TABLES TO wellbe_vault;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION vault.reject_mutation() RETURNS TRIGGER AS $$
        BEGIN
          RAISE EXCEPTION
            'raw_context_events is append-only: UPDATE and DELETE are forbidden';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_raw_context_events_immutable
          BEFORE UPDATE OR DELETE ON vault.raw_context_events
          FOR EACH ROW EXECUTE FUNCTION vault.reject_mutation();
    """)

    op.execute("""
        ALTER TABLE vault.raw_context_events ENABLE ROW LEVEL SECURITY;

        CREATE POLICY patient_isolation ON vault.raw_context_events
          USING (patient_id::text = current_setting('app.patient_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS patient_isolation ON vault.raw_context_events")
    op.execute("DROP TRIGGER IF EXISTS trg_raw_context_events_immutable ON vault.raw_context_events")
    op.execute("DROP FUNCTION IF EXISTS vault.reject_mutation()")
    op.drop_index("ix_raw_context_events_patient_hash", table_name="raw_context_events", schema="vault")
    op.drop_index("ix_raw_context_events_patient_created", table_name="raw_context_events", schema="vault")
    op.drop_table("raw_context_events", schema="vault")
    op.drop_table("raw_context_source_types", schema="vault")
    op.execute("DROP SCHEMA IF EXISTS vault")
    op.execute("""
        REVOKE ALL ON SCHEMA vault FROM wellbe_vault;
        -- Role wellbe_vault is left intact to avoid dropping a shared role.
    """)
