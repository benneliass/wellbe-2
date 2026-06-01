from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from wellbe_db import Base


class CorrectionRow(Base):
    __tablename__ = "corrections"
    __table_args__ = ({"schema": "c11"},)

    correction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(Text(), nullable=False)
    correction_type: Mapped[str] = mapped_column(Text(), nullable=False)
    actor_authority: Mapped[str] = mapped_column(Text(), nullable=False)
    actor_ref: Mapped[dict] = mapped_column(JSONB(), nullable=False, default=dict)
    grant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    role_binding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    raw_correction_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    rationale: Mapped[str | None] = mapped_column(Text(), nullable=True)
    proposed_payload: Mapped[dict] = mapped_column(JSONB(), nullable=False, default=dict)
    accepted_by_controller_actor: Mapped[dict | None] = mapped_column(
        JSONB(), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    effective_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    supersedes_correction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("c11.corrections.correction_id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)


class CorrectionTargetRow(Base):
    __tablename__ = "correction_targets"
    __table_args__ = ({"schema": "c11"},)

    correction_target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    correction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("c11.corrections.correction_id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_kind: Mapped[str] = mapped_column(Text(), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_version: Mapped[str | None] = mapped_column(Text(), nullable=True)
    field_path: Mapped[str | None] = mapped_column(Text(), nullable=True)
    base_value_hash: Mapped[str | None] = mapped_column(Text(), nullable=True)
    proposed_value_hash: Mapped[str | None] = mapped_column(Text(), nullable=True)
    semantic_rank: Mapped[int] = mapped_column(SmallInteger(), nullable=False, default=50)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CorrectionResolutionEventRow(Base):
    __tablename__ = "correction_resolution_events"
    __table_args__ = ({"schema": "c11"},)

    resolution_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    correction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("c11.corrections.correction_id"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_kind: Mapped[str] = mapped_column(Text(), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    field_path: Mapped[str | None] = mapped_column(Text(), nullable=True)
    resolution_action: Mapped[str] = mapped_column(Text(), nullable=False)
    prior_active_correction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    new_active_correction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
