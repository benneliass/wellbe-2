from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from wellbe_contracts.c3_ingestion import AdapterProvenance
from wellbe_contracts.primitives import (
    ActorId,
    AwareDatetime,
    CapturedAt,
    ConsentSnapshotId,
    EventId,
    GrantId,
    IngestedAt,
    PatientId,
    ReceivedAt,
)


# Event type constants — consumed by C4 dispatcher
RAW_CONTEXT_RECEIVED = "raw_context.received"


class RawContextEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: EventId
    patient_id: PatientId
    tenant_id: Optional[UUID] = None
    actor_id: ActorId
    source_type: str
    source_id: Optional[str] = None
    external_source_id: Optional[str] = None
    idempotency_key: str
    captured_at: CapturedAt
    received_at: ReceivedAt
    ingested_at: IngestedAt
    content_hash: str
    hash_scope: str = "patient"
    blob_ref: Optional[str] = None
    blob_bucket: Optional[str] = None
    blob_key: Optional[str] = None
    blob_version_id: Optional[str] = None
    byte_size: int
    mime_type: str
    encoding: Optional[str] = None
    language: Optional[str] = None
    original_filename_hash: Optional[str] = None
    source_metadata: Optional[dict] = None
    adapter_name: str
    adapter_version: str
    ingestor_version: str
    consent_snapshot_id: ConsentSnapshotId
    share_grant_id: Optional[GrantId] = None
    encryption_key_id: str
    encryption_key_version: int
    retention_policy_id: Optional[str] = None
    correlation_id: str
    trace_id: str
    duplicate_of_event_id: Optional[EventId] = None
    schema_version: int = 1
    created_at: AwareDatetime


class VaultWriteRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: PatientId
    actor_id: ActorId
    normalized_payload: bytes
    adapter_provenance: AdapterProvenance
    idempotency_key: str
    consent_snapshot_id: ConsentSnapshotId
    share_grant_id: Optional[GrantId] = None
    correlation_id: str
    trace_id: str
    mime_type: str
    encoding: Optional[str] = None
    language: Optional[str] = None
    original_filename_hash: Optional[str] = None
    source_metadata: Optional[dict] = None


class VaultWriteResponse(BaseModel):
    event_id: EventId
    content_hash: str
    duplicate_of_event_id: Optional[EventId] = None
    ingested_at: AwareDatetime
