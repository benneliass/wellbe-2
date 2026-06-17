from __future__ import annotations

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
    tenant_id: UUID | None = None
    actor_id: ActorId
    source_type: str
    source_id: str | None = None
    external_source_id: str | None = None
    idempotency_key: str
    captured_at: CapturedAt
    received_at: ReceivedAt
    ingested_at: IngestedAt
    content_hash: str
    hash_scope: str = "patient"
    blob_ref: str | None = None
    blob_bucket: str | None = None
    blob_key: str | None = None
    blob_version_id: str | None = None
    byte_size: int
    mime_type: str
    encoding: str | None = None
    language: str | None = None
    original_filename_hash: str | None = None
    source_metadata: dict | None = None
    adapter_name: str
    adapter_version: str
    ingestor_version: str
    consent_snapshot_id: ConsentSnapshotId
    share_grant_id: GrantId | None = None
    encryption_key_id: str
    encryption_key_version: int
    retention_policy_id: str | None = None
    correlation_id: str
    trace_id: str
    duplicate_of_event_id: EventId | None = None
    schema_version: int = 1
    created_at: AwareDatetime


class VaultWriteRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: PatientId
    actor_id: ActorId
    normalized_payload: bytes
    adapter_provenance: AdapterProvenance
    idempotency_key: str
    # When set, the durable Vault id is deterministic (uuid5 of the natural key)
    # and the append is idempotent via ON CONFLICT — the systemic guard against
    # permanent duplicate raw records under at-least-once delivery. When unset,
    # the legacy content-hash dedupe path is used (back-compat for direct ingest).
    event_id: EventId | None = None
    consent_snapshot_id: ConsentSnapshotId
    share_grant_id: GrantId | None = None
    correlation_id: str
    trace_id: str
    mime_type: str
    encoding: str | None = None
    language: str | None = None
    original_filename_hash: str | None = None
    source_metadata: dict | None = None


class VaultWriteResponse(BaseModel):
    event_id: EventId
    content_hash: str
    duplicate_of_event_id: EventId | None = None
    ingested_at: AwareDatetime
