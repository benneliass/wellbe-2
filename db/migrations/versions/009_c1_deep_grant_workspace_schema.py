"""C1/C17 deep Grant/Role workspace schema.

Implements the approved WEL-131 decision:
docs/decisions/deep-grant-role-workspace-model.md

Additive only. Existing consent.share_grants remains the lifecycle header; this
migration adds first-class Role/Workspace tables, versioned scope policy rows,
normalized grant selectors, capability/contribution policy rows, and separate
institution/research governance tables. Workspace membership never grants data
access by itself.

Revision ID: 009
Revises: 008
Create Date: 2026-06-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Migration DDL favors exact SQL/check-constraint readability over wrapping.
# ruff: noqa: E501

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS access")
    op.execute("CREATE SCHEMA IF NOT EXISTS workspace")
    op.execute("CREATE SCHEMA IF NOT EXISTS institution")
    op.execute("CREATE SCHEMA IF NOT EXISTS research")

    op.create_table(
        "role_types",
        sa.Column("role_type", sa.Text(), primary_key=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "may_receive_grant_types",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "may_control_data",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.CheckConstraint(
            "role_type IN ('individual_controller','caregiver','clinician','care_team','institution','researcher')",
            name="ck_role_type",
        ),
        schema="access",
    )

    op.execute("""
        INSERT INTO access.role_types
            (role_type, description, may_receive_grant_types, may_control_data)
        VALUES
            ('individual_controller', 'Individual data controller', ARRAY['controller_entitlement'], true),
            ('caregiver', 'Caregiver recipient role', ARRAY['delegated_individual','workspace_share'], false),
            ('clinician', 'Clinician recipient role', ARRAY['workspace_share'], false),
            ('care_team', 'Care team recipient role', ARRAY['workspace_share'], false),
            ('institution', 'Aggregate-only institution role', ARRAY['institution_aggregate'], false),
            ('researcher', 'Protocol-governed researcher role', ARRAY['research_sandbox'], false)
        ON CONFLICT (role_type) DO NOTHING;
    """)

    op.create_table(
        "role_bindings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role_type",
            sa.Text(),
            sa.ForeignKey("access.role_types.role_type"),
            nullable=False,
        ),
        sa.Column("subject_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("credential_ref", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending','active','suspended','revoked')",
            name="ck_role_binding_status",
        ),
        sa.CheckConstraint(
            "(role_type = 'individual_controller' AND subject_user_id IS NOT NULL) OR role_type <> 'individual_controller'",
            name="ck_controller_role_has_subject",
        ),
        schema="access",
    )
    op.create_index(
        "ix_role_bindings_actor_role",
        "role_bindings",
        ["actor_id", "role_type", "status"],
        schema="access",
    )

    op.create_table(
        "workspaces",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workspace_type", sa.Text(), nullable=False),
        sa.Column("controller_model", sa.Text(), nullable=False),
        sa.Column("subject_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_by_role_binding_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("access.role_bindings.id"),
            nullable=False,
        ),
        sa.Column(
            "policy_profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "default_expiry_policy",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "workspace_type IN ('individual','clinician_case_investigation','shared_health_thread','institution_continuity','research_sandbox')",
            name="ck_workspace_type",
        ),
        sa.CheckConstraint(
            "controller_model IN ('single_individual','multi_individual_consent_derived','aggregate_only')",
            name="ck_workspace_controller_model",
        ),
        sa.CheckConstraint(
            "status IN ('active','archived','suspended')",
            name="ck_workspace_status",
        ),
        schema="workspace",
    )

    op.create_table(
        "workspace_memberships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspace.workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "role_binding_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("access.role_bindings.id"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "invited_by_role_binding_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("access.role_bindings.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("workspace_id", "role_binding_id", name="uq_workspace_membership"),
        sa.CheckConstraint(
            "status IN ('invited','active','suspended','removed')",
            name="ck_workspace_membership_status",
        ),
        schema="workspace",
    )

    op.add_column(
        "share_grants",
        sa.Column("grant_type", sa.Text(), nullable=True),
        schema="consent",
    )
    op.add_column(
        "share_grants",
        sa.Column(
            "recipient_role_binding_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema="consent",
    )
    op.add_column(
        "share_grants",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="consent",
    )
    op.add_column(
        "share_grants",
        sa.Column("purpose_code", sa.Text(), nullable=True),
        schema="consent",
    )
    op.add_column(
        "share_grants",
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        schema="consent",
    )
    op.add_column(
        "share_grants",
        sa.Column("consent_snapshot_hash", sa.Text(), nullable=True),
        schema="consent",
    )
    op.add_column(
        "share_grants",
        sa.Column("policy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="consent",
    )
    op.add_column(
        "share_grants",
        sa.Column(
            "authz_epoch",
            sa.BigInteger(),
            nullable=False,
            server_default="1",
        ),
        schema="consent",
    )
    op.add_column(
        "share_grants",
        sa.Column(
            "aggregate_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema="consent",
    )
    op.create_foreign_key(
        "fk_share_grants_recipient_role_binding",
        "share_grants",
        "role_bindings",
        ["recipient_role_binding_id"],
        ["id"],
        source_schema="consent",
        referent_schema="access",
    )
    op.create_foreign_key(
        "fk_share_grants_workspace",
        "share_grants",
        "workspaces",
        ["workspace_id"],
        ["id"],
        source_schema="consent",
        referent_schema="workspace",
    )
    op.create_check_constraint(
        "ck_share_grants_grant_type",
        "share_grants",
        "grant_type IS NULL OR grant_type IN ('controller_entitlement','delegated_individual','workspace_share','institution_aggregate','research_sandbox')",
        schema="consent",
    )

    op.create_table(
        "scope_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("scope_code", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("allowed_workspace_types", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("allowed_role_types", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("requires_explicit_resource_set", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("includes_raw_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("default_export_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.Text(), nullable=False),
        sa.UniqueConstraint("scope_code", "version", name="uq_scope_profile_code_version"),
        schema="consent",
    )

    op.create_table(
        "scope_profile_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scope_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("consent.scope_profiles.id"), nullable=False),
        sa.Column("consent_scope_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("consent.consent_scopes.id"), nullable=True),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("data_category", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("include_security_labels", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("exclude_security_labels", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("requires_selector_type", sa.Text(), nullable=True),
        schema="consent",
    )

    op.create_table(
        "grant_scope_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("grant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("consent.share_grants.id"), nullable=False),
        sa.Column("scope_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("consent.scope_profiles.id"), nullable=False),
        sa.Column("selector_type", sa.Text(), nullable=False),
        sa.Column("selector_hash", sa.Text(), nullable=False),
        sa.Column("time_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_data_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        schema="consent",
    )

    for table_name, columns in {
        "grant_scope_resources": [
            sa.Column("resource_type", sa.Text(), nullable=False),
            sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        ],
        "grant_scope_categories": [
            sa.Column("data_category", sa.Text(), nullable=False),
        ],
        "grant_scope_labels": [
            sa.Column("label_type", sa.Text(), nullable=False),
            sa.Column("security_label", sa.Text(), nullable=False),
        ],
    }.items():
        op.create_table(
            table_name,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "grant_scope_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("consent.grant_scope_instances.id"),
                nullable=False,
            ),
            *columns,
            schema="consent",
        )

    op.create_table(
        "grant_capabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("grant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("consent.share_grants.id"), nullable=False),
        sa.Column("capability", sa.Text(), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("constraints", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("requires_controller_acceptance", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("grant_id", "capability", name="uq_grant_capability"),
        schema="consent",
    )

    op.create_table(
        "grant_contribution_policies",
        sa.Column("grant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("consent.share_grants.id"), primary_key=True),
        sa.Column("contribution_mode", sa.Text(), nullable=False),
        sa.Column("allowed_target_categories", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("requires_c11_review", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.CheckConstraint(
            "contribution_mode IN ('external_annotation_only','pending_controller_acceptance','direct_write_allowed_for_controller_only')",
            name="ck_contribution_mode",
        ),
        schema="consent",
    )

    op.create_table(
        "aggregate_inclusion_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose_code", sa.Text(), nullable=False),
        sa.Column("data_categories", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("cohort_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_snapshot_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        schema="institution",
    )

    op.create_table(
        "materialized_aggregate_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cohort_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_code", sa.Text(), nullable=False),
        sa.Column("time_bucket", postgresql.TSTZRANGE(), nullable=False),
        sa.Column("consented_subject_count", sa.Integer(), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("privacy_mechanism", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="institution",
    )

    op.create_table(
        "protocols",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("sponsor_org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("governance_status", sa.Text(), nullable=False),
        sa.Column("review_body_ref", sa.Text(), nullable=True),
        sa.Column("purpose_code", sa.Text(), nullable=False),
        sa.Column("data_categories", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("allowed_transformations", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("retention_policy", postgresql.JSONB(), nullable=False),
        sa.Column("export_policy", postgresql.JSONB(), nullable=False),
        sa.Column("consent_form_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="research",
    )

    op.create_table(
        "protocol_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("protocol_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research.protocols.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_effect", sa.Text(), nullable=False),
        sa.Column("consent_snapshot_hash", sa.Text(), nullable=False),
        sa.Column("signed_by_role_binding_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("access.role_bindings.id"), nullable=False),
        schema="research",
    )

    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'wellbe_access') THEN
            CREATE ROLE wellbe_access LOGIN PASSWORD 'wellbe_dev';
          END IF;
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'wellbe_institution') THEN
            CREATE ROLE wellbe_institution LOGIN PASSWORD 'wellbe_dev';
          END IF;
        END $$;

        GRANT USAGE ON SCHEMA access, workspace, consent, research TO wellbe_access;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA access TO wellbe_access;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA workspace TO wellbe_access;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA consent TO wellbe_access;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA research TO wellbe_access;

        -- Institution runtime role receives aggregate-only access. It is not granted
        -- access to personal schemas such as vault/evidence/graph/processing.
        GRANT USAGE ON SCHEMA institution TO wellbe_institution;
        GRANT SELECT ON institution.materialized_aggregate_metrics TO wellbe_institution;
    """)


def downgrade() -> None:
    op.execute("REVOKE ALL ON SCHEMA institution FROM wellbe_institution")
    op.drop_table("protocol_consents", schema="research")
    op.drop_table("protocols", schema="research")
    op.drop_table("materialized_aggregate_metrics", schema="institution")
    op.drop_table("aggregate_inclusion_consents", schema="institution")
    op.drop_table("grant_contribution_policies", schema="consent")
    op.drop_table("grant_capabilities", schema="consent")
    op.drop_table("grant_scope_labels", schema="consent")
    op.drop_table("grant_scope_categories", schema="consent")
    op.drop_table("grant_scope_resources", schema="consent")
    op.drop_table("grant_scope_instances", schema="consent")
    op.drop_table("scope_profile_items", schema="consent")
    op.drop_table("scope_profiles", schema="consent")
    op.drop_constraint("ck_share_grants_grant_type", "share_grants", schema="consent")
    op.drop_constraint("fk_share_grants_workspace", "share_grants", schema="consent", type_="foreignkey")
    op.drop_constraint("fk_share_grants_recipient_role_binding", "share_grants", schema="consent", type_="foreignkey")
    for column in (
        "aggregate_only",
        "authz_epoch",
        "policy_version_id",
        "consent_snapshot_hash",
        "effective_at",
        "purpose_code",
        "workspace_id",
        "recipient_role_binding_id",
        "grant_type",
    ):
        op.drop_column("share_grants", column, schema="consent")
    op.drop_table("workspace_memberships", schema="workspace")
    op.drop_table("workspaces", schema="workspace")
    op.drop_table("role_bindings", schema="access")
    op.drop_table("role_types", schema="access")
    op.execute("DROP SCHEMA IF EXISTS research")
    op.execute("DROP SCHEMA IF EXISTS institution")
    op.execute("DROP SCHEMA IF EXISTS workspace")
    op.execute("DROP SCHEMA IF EXISTS access")
