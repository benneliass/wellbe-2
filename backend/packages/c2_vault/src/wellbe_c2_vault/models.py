from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from wellbe_db import Base, UUIDPrimaryKeyMixin


class SourceTypeRow(Base):
    __tablename__ = "raw_context_source_types"
    __table_args__ = {"schema": "vault"}

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default="active")
    requires_blob: Mapped[bool] = mapped_column(Boolean, server_default="false")
    default_mime_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default="{}"
    )


class RawContextEventRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "raw_context_events"
    __table_args__ = {"schema": "vault"}

    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    source_type: Mapped[str] = mapped_column(
        Text, ForeignKey("vault.raw_context_source_types.code")
    )
    source_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_source_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(Text, unique=True)
    captured_at: Mapped[datetime] = mapped_column()
    received_at: Mapped[datetime] = mapped_column()
    ingested_at: Mapped[datetime] = mapped_column()
    content_hash: Mapped[str] = mapped_column(Text)
    hash_scope: Mapped[str] = mapped_column(Text, server_default="patient")
    blob_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    blob_bucket: Mapped[str | None] = mapped_column(Text, nullable=True)
    blob_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    blob_version_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    byte_size: Mapped[int] = mapped_column(BigInteger)
    mime_type: Mapped[str] = mapped_column(Text)
    encoding: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_metadata: Mapped[dict | None] = mapped_column(JSONB, server_default="{}")
    adapter_name: Mapped[str] = mapped_column(Text)
    adapter_version: Mapped[str] = mapped_column(Text)
    ingestor_version: Mapped[str] = mapped_column(Text, server_default="0.1.0")
    consent_snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    share_grant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    encryption_key_id: Mapped[str] = mapped_column(Text)
    encryption_key_version: Mapped[int] = mapped_column(Integer, server_default="1")
    retention_policy_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str] = mapped_column(Text)
    trace_id: Mapped[str] = mapped_column(Text)
    duplicate_of_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vault.raw_context_events.id"),
        nullable=True,
    )
    schema_version: Mapped[int] = mapped_column(Integer, server_default="1")
    created_at: Mapped[datetime] = mapped_column()
