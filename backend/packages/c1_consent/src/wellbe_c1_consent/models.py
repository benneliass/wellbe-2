from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
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
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)


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
