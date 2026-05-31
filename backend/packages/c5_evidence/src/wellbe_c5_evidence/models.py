from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, Integer, Text, CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from wellbe_db import Base


class EvidenceLinkRow(Base):
    __tablename__ = "evidence_links"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_evidence_confidence_range",
        ),
        CheckConstraint(
            "link_type IN ('primary', 'corroborating', 'contradicting', 'contextual')",
            name="ck_evidence_link_type",
        ),
        CheckConstraint(
            "source_type IN ('extracted_fact', 'health_signal', 'memory_entry', 'ai_summary', 'ai_response')",
            name="ck_evidence_source_type",
        ),
        CheckConstraint(
            "confidence_basis IN ('extraction_model', 'user_confirmation', 'clinical_source', 'system_computed', 'correction_service')",
            name="ck_evidence_confidence_basis",
        ),
        CheckConstraint(
            "linked_by IN ('user', 'system', 'pipeline', 'correction_service')",
            name="ck_evidence_linked_by",
        ),
        UniqueConstraint(
            "source_type",
            "source_id",
            "raw_context_event_id",
            "link_type",
            name="uq_evidence_link_dedup",
        ),
        {"schema": "evidence"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(Text(), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    raw_context_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vault.raw_context_events.id"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    link_type: Mapped[str] = mapped_column(Text(), nullable=False)
    confidence: Mapped[float] = mapped_column(Float(), nullable=False)
    confidence_basis: Mapped[str] = mapped_column(Text(), nullable=False)
    relevance_span_start: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    relevance_span_end: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(nullable=False)
    linked_by: Mapped[str] = mapped_column(Text(), nullable=False)
    correction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
