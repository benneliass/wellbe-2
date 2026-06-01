from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from wellbe_db import Base


class PendingItemRow(Base):
    __tablename__ = "pending_items"
    __table_args__ = ({"schema": "c9"},)

    pending_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    primary_thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    item_type: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[str] = mapped_column(Text(), nullable=False)
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    next_action_code: Mapped[str | None] = mapped_column(Text(), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_precision: Mapped[str] = mapped_column(Text(), nullable=False, default="unknown")
    owner_ref: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    contact_ref: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    source_ref: Mapped[dict] = mapped_column(JSONB(), nullable=False, default=dict)
    evidence_refs: Mapped[list] = mapped_column(JSONB(), nullable=False, default=list)
    investigation_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    latest_observed_thread_transition_seq: Mapped[int | None] = mapped_column(
        BigInteger(), nullable=True
    )
    latest_observed_thread_status_version: Mapped[int | None] = mapped_column(
        BigInteger(), nullable=True
    )
    blocks_c9_closure_request: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=False
    )
    normal_test_safety_net: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=False
    )
    symptoms_persist_state: Mapped[str] = mapped_column(
        Text(), nullable=False, default="unknown"
    )
    timer_epoch: Mapped[int] = mapped_column(BigInteger(), nullable=False, default=0)
    workflow_id: Mapped[str | None] = mapped_column(Text(), nullable=True, unique=True)
    workflow_run_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    version: Mapped[int] = mapped_column(BigInteger(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)


class PendingItemEventRow(Base):
    __tablename__ = "pending_item_events"
    __table_args__ = ({"schema": "c9"},)

    pending_item_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pending_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("c9.pending_items.pending_item_id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(Text(), nullable=False)
    event_payload: Mapped[dict] = mapped_column(JSONB(), nullable=False, default=dict)
    actor: Mapped[dict] = mapped_column(JSONB(), nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)


class ConsumedThreadEventRow(Base):
    __tablename__ = "consumed_thread_events"
    __table_args__ = ({"schema": "c9"},)

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    transition_seq: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TimerActionRow(Base):
    __tablename__ = "timer_actions"
    __table_args__ = ({"schema": "c9"},)

    timer_action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pending_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("c9.pending_items.pending_item_id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    timer_epoch: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    action_type: Mapped[str] = mapped_column(Text(), nullable=False)
    c7_transition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    c7_rejection_code: Mapped[str | None] = mapped_column(Text(), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB(), nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
