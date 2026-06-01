from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from wellbe_db import Base


class InvestigationRow(Base):
    __tablename__ = "investigations"
    __table_args__ = ({"schema": "c14"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    primary_question: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[str] = mapped_column(Text(), nullable=False, default="open")
    status_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    status_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    owner_type: Mapped[str] = mapped_column(Text(), nullable=False)
    owner_grant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    scope: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False, default=dict)
    evidence_bundle_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    active_theory_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    pending_item_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    missing_context_items: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB(), nullable=False, default=list
    )
    safety_flags: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB(), nullable=False, default=list
    )
    outputs: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False, default=dict)
    projection_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_review_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_under_grant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    status_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvestigationThreadRow(Base):
    __tablename__ = "investigation_threads"
    __table_args__ = ({"schema": "c14"},)

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("c14.investigations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship: Mapped[str] = mapped_column(Text(), nullable=False, default="primary")
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvestigationStateTransitionRow(Base):
    __tablename__ = "investigation_state_transitions"
    __table_args__ = (
        UniqueConstraint(
            "investigation_id", "transition_seq", name="uq_investigation_transition_seq"
        ),
        UniqueConstraint(
            "investigation_id", "idempotency_key", name="uq_investigation_idempotency_key"
        ),
        {"schema": "c14"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("c14.investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    from_status: Mapped[str] = mapped_column(Text(), nullable=False)
    to_status: Mapped[str] = mapped_column(Text(), nullable=False)
    transition_seq: Mapped[int] = mapped_column(Integer(), nullable=False)
    reason_code: Mapped[str] = mapped_column(Text(), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(Text(), nullable=False)
    correlation_id: Mapped[str] = mapped_column(Text(), nullable=False)
    event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvestigationParticipantRow(Base):
    __tablename__ = "investigation_participants"
    __table_args__ = (
        UniqueConstraint(
            "investigation_id", "actor_id", "role", name="uq_investigation_participant"
        ),
        {"schema": "c14"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("c14.investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(Text(), nullable=False)
    grant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(Text(), nullable=False, default="active")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
