from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from wellbe_db import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConsentScopeRow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "consent_scopes"
    __table_args__ = {"schema": "consent"}

    subject_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(Text, nullable=False)
    data_category: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text)
    grant_source: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column()
    revoked_at: Mapped[datetime | None] = mapped_column()
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ShareGrantRow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "share_grants"
    __table_args__ = (
        CheckConstraint(
            "grantee_type IN ('user','clinician','email_invite','org')",
            name="ck_share_grants_grantee_type",
        ),
        CheckConstraint(
            "status IN ('pending','active','expired','revoked')",
            name="ck_share_grants_status",
        ),
        {"schema": "consent"},
    )

    grantor_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    grantee_user_id: Mapped[uuid.UUID | None] = mapped_column()
    grantee_identifier_hash: Mapped[str | None] = mapped_column(Text)
    grantee_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    resource_selector: Mapped[str | None] = mapped_column(Text)
    thread_ids: Mapped[list] = mapped_column(JSONB, default=list)
    actions: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    data_categories: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column()
    accepted_at: Mapped[datetime | None] = mapped_column()
    revoked_at: Mapped[datetime | None] = mapped_column()
    revoked_by: Mapped[uuid.UUID | None] = mapped_column()
    revocation_reason: Mapped[str | None] = mapped_column(Text)
    consent_snapshot_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    grant_token_hash: Mapped[str | None] = mapped_column(Text)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column()
    grant_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)


class RevocationLogRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "revocation_log"
    __table_args__ = {"schema": "consent"}

    grant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent.share_grants.id"), nullable=False
    )
    revoked_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)


class PatientPrivacyPreferenceRow(Base):
    __tablename__ = "patient_privacy_preferences"
    __table_args__ = (
        CheckConstraint(
            "status IN ('disabled','enabled','revoked')",
            name="ck_patient_privacy_status",
        ),
        {"schema": "consent"},
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    capability: Mapped[str] = mapped_column(Text, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="disabled")
    enabled_at: Mapped[datetime | None] = mapped_column()
    revoked_at: Mapped[datetime | None] = mapped_column()
    purpose: Mapped[str | None] = mapped_column(Text)
    consent_text_version: Mapped[str | None] = mapped_column(Text)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class AccountRow(UUIDPrimaryKeyMixin, Base):
    """The WellBe controller account, keyed on the OIDC (issuer, subject) identifier.

    ``controller_patient_id`` is the patient id used across every other schema. It
    is stored explicitly (rather than reusing ``id``) so a known federated identity
    — e.g. the seeded dev workspace — can map to a pre-existing patient.
    """

    __tablename__ = "accounts"
    __table_args__ = ({"schema": "identity"},)

    issuer: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    controller_patient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class OnboardingSessionRow(UUIDPrimaryKeyMixin, Base):
    """Pending->active onboarding draft. Nothing is effective until ``status`` is
    ``active`` (set atomically on final confirmation)."""

    __tablename__ = "onboarding_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','active','abandoned')",
            name="ck_onboarding_status",
        ),
        {"schema": "identity"},
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("identity.accounts.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    consent_version: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[dict] = mapped_column(JSONB, default=dict)
    baseline: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finalized_at: Mapped[datetime | None] = mapped_column()


class RoleBindingRow(Base):
    """access.role_bindings — who can act in what role. Membership never grants
    data access by itself (that is a grant); this binds an actor to a role."""

    __tablename__ = "role_bindings"
    __table_args__ = ({"schema": "access"},)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    role_type: Mapped[str] = mapped_column(
        Text, ForeignKey("access.role_types.role_type"), nullable=False
    )
    subject_user_id: Mapped[uuid.UUID | None] = mapped_column()
    organization_id: Mapped[uuid.UUID | None] = mapped_column()
    credential_ref: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    verified_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class WorkspaceRow(Base):
    """workspace.workspaces — a scoped surface an actor can act in. The personal
    (``individual``) workspace is the always-present, personal-first default."""

    __tablename__ = "workspaces"
    __table_args__ = ({"schema": "workspace"},)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_type: Mapped[str] = mapped_column(Text, nullable=False)
    controller_model: Mapped[str] = mapped_column(Text, nullable=False)
    subject_user_id: Mapped[uuid.UUID | None] = mapped_column()
    created_by_role_binding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("access.role_bindings.id"), nullable=False
    )
    policy_profile_id: Mapped[uuid.UUID | None] = mapped_column()
    default_expiry_policy: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class WorkspaceMembershipRow(Base):
    """workspace.workspace_memberships — an actor's membership of a workspace via a
    role binding. Membership is presence, not data access."""

    __tablename__ = "workspace_memberships"
    __table_args__ = ({"schema": "workspace"},)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id"), nullable=False
    )
    role_binding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("access.role_bindings.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    invited_by_role_binding_id: Mapped[uuid.UUID | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
