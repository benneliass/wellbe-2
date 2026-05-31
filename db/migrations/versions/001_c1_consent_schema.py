"""Create C1 consent schema and tables.

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-05-31
"""
from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS consent")

    op.execute("""
        CREATE TABLE consent.consent_scopes (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            subject_id      UUID NOT NULL,
            resource_type   TEXT NOT NULL,
            resource_id     UUID,
            action          TEXT NOT NULL,
            data_category   TEXT NOT NULL,
            purpose         TEXT,
            grant_source    TEXT NOT NULL,
            valid_from      TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_until     TIMESTAMPTZ,
            revoked_at      TIMESTAMPTZ,
            policy_version  INT NOT NULL DEFAULT 1,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE INDEX ix_consent_scopes_lookup
            ON consent.consent_scopes (subject_id, resource_type, action)
    """)

    op.execute("""
        CREATE TABLE consent.share_grants (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            grantor_id              UUID NOT NULL,
            grantee_user_id         UUID,
            grantee_identifier_hash TEXT,
            grantee_type            TEXT NOT NULL
                                        CHECK (grantee_type IN ('user','clinician','email_invite','org')),
            status                  TEXT NOT NULL DEFAULT 'pending'
                                        CHECK (status IN ('pending','active','expired','revoked')),
            resource_selector       TEXT,
            thread_ids              JSONB DEFAULT '[]',
            actions                 TEXT[] NOT NULL,
            data_categories         TEXT[] NOT NULL,
            purpose                 TEXT,
            expires_at              TIMESTAMPTZ,
            accepted_at             TIMESTAMPTZ,
            revoked_at              TIMESTAMPTZ,
            revoked_by              UUID,
            revocation_reason       TEXT,
            consent_snapshot_id     UUID NOT NULL,
            grant_token_hash        TEXT,
            policy_version          INT NOT NULL DEFAULT 1,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by              UUID NOT NULL,
            last_accessed_at        TIMESTAMPTZ,
            metadata                JSONB DEFAULT '{}'
        )
    """)

    op.execute("""
        CREATE INDEX ix_share_grants_grantor
            ON consent.share_grants (grantor_id, status)
    """)

    op.execute("""
        CREATE INDEX ix_share_grants_grantee
            ON consent.share_grants (grantee_user_id, status)
    """)

    op.execute("""
        CREATE TABLE consent.revocation_log (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            grant_id    UUID NOT NULL REFERENCES consent.share_grants(id),
            revoked_by  UUID NOT NULL,
            revoked_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            reason      TEXT,
            event_type  TEXT NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE consent.patient_privacy_preferences (
            patient_id            UUID NOT NULL,
            capability            TEXT NOT NULL,
            status                TEXT NOT NULL DEFAULT 'disabled'
                                      CHECK (status IN ('disabled','enabled','revoked')),
            enabled_at            TIMESTAMPTZ,
            revoked_at            TIMESTAMPTZ,
            purpose               TEXT,
            consent_text_version  TEXT,
            policy_version        INT NOT NULL DEFAULT 1,
            PRIMARY KEY (patient_id, capability)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS consent.patient_privacy_preferences")
    op.execute("DROP TABLE IF EXISTS consent.revocation_log")
    op.execute("DROP TABLE IF EXISTS consent.share_grants")
    op.execute("DROP TABLE IF EXISTS consent.consent_scopes")
    op.execute("DROP SCHEMA IF EXISTS consent")
