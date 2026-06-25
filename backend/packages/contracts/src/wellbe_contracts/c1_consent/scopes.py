from __future__ import annotations

import enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from wellbe_contracts.primitives import (
    AwareDatetime,
    ConsentSnapshotId,
    GrantId,
    PatientId,
)


class ConsentScope(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject_id: PatientId
    resource_type: str
    resource_id: UUID | None = None
    action: str
    data_category: str
    purpose: str
    grant_source: str
    valid_from: AwareDatetime
    valid_until: AwareDatetime | None = None
    revoked_at: AwareDatetime | None = None
    policy_version: str


class ShareGrantStatus(enum.StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class GranteeType(enum.StrEnum):
    USER = "user"
    CLINICIAN = "clinician"
    EMAIL_INVITE = "email_invite"
    ORG = "org"


class ShareGrant(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: GrantId
    grantor_id: PatientId
    grantee_user_id: UUID | None = None
    grantee_identifier_hash: str | None = None
    grantee_type: GranteeType
    status: ShareGrantStatus
    resource_selector: str | None = None
    thread_ids: list[UUID]
    actions: list[str]
    data_categories: list[str]
    purpose: str
    expires_at: AwareDatetime | None = None
    accepted_at: AwareDatetime | None = None
    revoked_at: AwareDatetime | None = None
    revoked_by: UUID | None = None
    revocation_reason: str | None = None
    consent_snapshot_id: ConsentSnapshotId
    grant_token_hash: str | None = None
    policy_version: str
    created_at: AwareDatetime
    created_by: UUID
    last_accessed_at: AwareDatetime | None = None
    metadata: dict[str, Any] | None = None


class RevocationEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    grant_id: GrantId
    revoked_by: UUID
    revoked_at: AwareDatetime
    reason: str
    event_type: str
