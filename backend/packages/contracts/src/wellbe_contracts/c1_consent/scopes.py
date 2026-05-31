from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional
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
    resource_id: Optional[UUID] = None
    action: str
    data_category: str
    purpose: str
    grant_source: str
    valid_from: AwareDatetime
    valid_until: Optional[AwareDatetime] = None
    revoked_at: Optional[AwareDatetime] = None
    policy_version: str


class ShareGrantStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class GranteeType(str, enum.Enum):
    USER = "user"
    CLINICIAN = "clinician"
    EMAIL_INVITE = "email_invite"
    ORG = "org"


class ShareGrant(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: GrantId
    grantor_id: PatientId
    grantee_user_id: Optional[UUID] = None
    grantee_identifier_hash: Optional[str] = None
    grantee_type: GranteeType
    status: ShareGrantStatus
    resource_selector: Optional[str] = None
    thread_ids: list[UUID]
    actions: list[str]
    data_categories: list[str]
    purpose: str
    expires_at: Optional[AwareDatetime] = None
    accepted_at: Optional[AwareDatetime] = None
    revoked_at: Optional[AwareDatetime] = None
    revoked_by: Optional[UUID] = None
    revocation_reason: Optional[str] = None
    consent_snapshot_id: ConsentSnapshotId
    grant_token_hash: Optional[str] = None
    policy_version: str
    created_at: AwareDatetime
    created_by: UUID
    last_accessed_at: Optional[AwareDatetime] = None
    metadata: Optional[dict] = None


class RevocationEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    grant_id: GrantId
    revoked_by: UUID
    revoked_at: AwareDatetime
    reason: str
    event_type: str
