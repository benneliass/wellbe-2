from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from wellbe_db import Base


class HealthThreadRow(Base):
    __tablename__ = "health_threads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active_unresolved','waiting_for_result','referred',"
            "'watchful_waiting','escalated','explained','chronic_monitoring',"
            "'closed','reopened','archived')",
            name="ck_health_thread_status",
        ),
        {"schema": "thread"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[str] = mapped_column(Text(), nullable=False, default="draft")
    status_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ThreadStateTransitionRow(Base):
    __tablename__ = "thread_state_transitions"
    __table_args__ = (
        UniqueConstraint("thread_id", "transition_seq", name="uq_thread_transition_seq"),
        UniqueConstraint("thread_id", "idempotency_key", name="uq_thread_idempotency_key"),
        {"schema": "thread"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("thread.health_threads.id"), nullable=False
    )
    from_status: Mapped[str] = mapped_column(Text(), nullable=False)
    to_status: Mapped[str] = mapped_column(Text(), nullable=False)
    transition_seq: Mapped[int] = mapped_column(Integer(), nullable=False)
    actor_type: Mapped[str] = mapped_column(Text(), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason_code: Mapped[str] = mapped_column(Text(), nullable=False)
    evidence_refs: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB(), nullable=False, default=list
    )
    safety_flags: Mapped[list[str]] = mapped_column(JSONB(), nullable=False, default=list)
    idempotency_key: Mapped[str] = mapped_column(Text(), nullable=False)
    correlation_id: Mapped[str] = mapped_column(Text(), nullable=False)
    event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HealthThreadAllowedTransitionRow(Base):
    __tablename__ = "health_thread_allowed_transitions"
    __table_args__ = ({"schema": "thread"},)

    from_status: Mapped[str] = mapped_column(Text(), primary_key=True)
    to_status: Mapped[str] = mapped_column(Text(), primary_key=True)
