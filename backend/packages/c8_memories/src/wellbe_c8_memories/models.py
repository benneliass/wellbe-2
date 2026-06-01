from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from wellbe_db import Base


class MemoryEntryRow(Base):
    __tablename__ = "memory_entries"
    __table_args__ = ({"schema": "c8"},)

    memory_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    memory_type: Mapped[str] = mapped_column(Text(), nullable=False)
    authorship_mode: Mapped[str] = mapped_column(Text(), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(Text(), nullable=False, default="draft")
    title: Mapped[str | None] = mapped_column(Text(), nullable=True)
    display_intent: Mapped[str] = mapped_column(
        Text(), nullable=False, default="memory_surface"
    )
    payload: Mapped[dict] = mapped_column(JSONB(), nullable=False, default=dict)
    source_version_hash: Mapped[str | None] = mapped_column(Text(), nullable=True)
    source_projection_version: Mapped[int] = mapped_column(
        BigInteger(), nullable=False, default=0
    )
    c10_gate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_by_actor: Mapped[dict] = mapped_column(JSONB(), nullable=False, default=dict)
    accepted_by_controller_actor: Mapped[dict | None] = mapped_column(
        JSONB(), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    visible_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)


class MemorySourceRefRow(Base):
    __tablename__ = "memory_source_refs"
    __table_args__ = ({"schema": "c8"},)

    memory_source_ref_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    memory_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("c8.memory_entries.memory_entry_id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_ref_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_ref_type: Mapped[str] = mapped_column(Text(), nullable=False)
    source_ref_version: Mapped[str | None] = mapped_column(Text(), nullable=True)
    field_path: Mapped[str | None] = mapped_column(Text(), nullable=True)
    link_role: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PatternMemoryRefRow(Base):
    __tablename__ = "pattern_memory_refs"
    __table_args__ = ({"schema": "c8"},)

    memory_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("c8.memory_entries.memory_entry_id", ondelete="CASCADE"),
        primary_key=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    min_current_score: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    current_score: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    current_score_asof: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_theory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    source_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    c10_gate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    safety_level: Mapped[str] = mapped_column(Text(), nullable=False)


class ResponsibilityMemoryRefRow(Base):
    __tablename__ = "responsibility_memory_refs"
    __table_args__ = ({"schema": "c8"},)

    memory_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("c8.memory_entries.memory_entry_id", ondelete="CASCADE"),
        primary_key=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    pending_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    pending_item_version: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    responsibility_role: Mapped[str] = mapped_column(Text(), nullable=False)
