"""C1 identity accounts + onboarding sessions, and personal-workspace idempotency.

Implements the approved onboarding decision:
docs/decisions/onboarding-consent-identity-flow.md (Spike WEL-183)

Additive only. Adds:
  * identity.accounts — the WellBe controller account, keyed on the OIDC
    (issuer, subject) federated identifier (NIST SP 800-63C). controller_patient_id
    is the patient id used across every other schema; for a new user it equals the
    account id, but it is stored explicitly so a known identity (e.g. the dev
    workspace) can map to a pre-existing seeded patient.
  * identity.onboarding_sessions — the pending->active onboarding draft. No consent
    scope, workspace, or grant becomes effective until status flips to 'active' on
    explicit final confirmation, so an abandoned flow leaves only a pending draft.

It also adds idempotency constraints so re-running onboarding finalize (at-least-once
delivery, refresh, back button) can never create a second personal workspace,
controller role binding, or duplicate core consent row for the same identity:
  * one 'individual' workspace per subject
  * one 'individual_controller' role binding per actor
  * one core onboarding consent row per (subject, resource_type, action, purpose)

Revision ID: 021
Revises: 020
Create Date: 2026-06-18
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Migration DDL favors exact SQL/check-constraint readability over wrapping.
# ruff: noqa: E501

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS identity")

    op.create_table(
        "accounts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("issuer", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("controller_patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Federated identity key — issuer MUST be part of the key (never subject or
        # email alone) so identities from different providers can never collide.
        sa.UniqueConstraint("issuer", "subject", name="uq_account_issuer_subject"),
        sa.UniqueConstraint("controller_patient_id", name="uq_account_controller_patient"),
        schema="identity",
    )

    op.create_table(
        "onboarding_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.accounts.id"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("consent_version", sa.Text(), nullable=False),
        sa.Column("choices", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("baseline", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        # One onboarding session per account: get_or_create + resume is idempotent.
        sa.UniqueConstraint("account_id", name="uq_onboarding_account"),
        sa.CheckConstraint(
            "status IN ('pending','active','abandoned')",
            name="ck_onboarding_status",
        ),
        schema="identity",
    )

    # --- Idempotency guards (additive to migration 009 tables) ---------------
    # One personal (individual) workspace per data subject. Partial unique so
    # other workspace types are unaffected.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_one_personal_workspace "
        "ON workspace.workspaces (subject_user_id) "
        "WHERE workspace_type = 'individual'"
    )
    # One active controller role binding per actor on their own subject.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_one_controller_binding "
        "ON access.role_bindings (actor_id) "
        "WHERE role_type = 'individual_controller'"
    )
    # One core onboarding consent row per (subject, resource_type, action, purpose),
    # so re-finalize with ON CONFLICT DO NOTHING never duplicates core scopes.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_onboarding_core_consent "
        "ON consent.consent_scopes (subject_id, resource_type, action, purpose) "
        "WHERE grant_source = 'onboarding'"
    )

    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'wellbe_access') THEN
            GRANT USAGE ON SCHEMA identity TO wellbe_access;
            GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA identity TO wellbe_access;
          END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS consent.ux_onboarding_core_consent")
    op.execute("DROP INDEX IF EXISTS access.ux_one_controller_binding")
    op.execute("DROP INDEX IF EXISTS workspace.ux_one_personal_workspace")
    op.drop_table("onboarding_sessions", schema="identity")
    op.drop_table("accounts", schema="identity")
    op.execute("DROP SCHEMA IF EXISTS identity")
