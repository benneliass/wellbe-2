from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, Integer, Boolean, Text, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from wellbe_db import Base


class ExtractedFactRow(Base):
    __tablename__ = "extracted_facts"
    __table_args__ = (
        CheckConstraint(
            "extraction_confidence >= 0 AND extraction_confidence <= 1",
            name="ck_fact_confidence_range",
        ),
        CheckConstraint(
            "quality_flag IN ('clean', 'low_confidence', 'requires_review', 'partial')",
            name="ck_fact_quality_flag",
        ),
        CheckConstraint(
            "subject IN ('patient', 'family_member', 'other')",
            name="ck_fact_subject",
        ),
        {"schema": "processing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    raw_context_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vault.raw_context_events.id"),
        nullable=False,
    )

    fact_type: Mapped[str] = mapped_column(Text(), nullable=False)
    entity_label: Mapped[str] = mapped_column(Text(), nullable=False)
    normalized_key: Mapped[str] = mapped_column(Text(), nullable=False)
    code_system: Mapped[str | None] = mapped_column(Text(), nullable=True)
    code: Mapped[str | None] = mapped_column(Text(), nullable=True)

    text_span_start: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    text_span_end: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    source_text_excerpt_hash: Mapped[str | None] = mapped_column(Text(), nullable=True)

    extraction_confidence: Mapped[float] = mapped_column(Float(), nullable=False)
    extraction_model: Mapped[str] = mapped_column(Text(), nullable=False)
    model_version: Mapped[str] = mapped_column(Text(), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(Text(), nullable=False)

    quality_flag: Mapped[str] = mapped_column(Text(), nullable=False)
    quality_metadata: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)

    is_negated: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    is_historical: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    is_hypothetical: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    subject: Mapped[str] = mapped_column(Text(), nullable=False, default="patient")

    captured_at: Mapped[datetime] = mapped_column(nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(nullable=False)
    correlation_id: Mapped[str] = mapped_column(Text(), nullable=False)
    trace_id: Mapped[str] = mapped_column(Text(), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class HealthSignalRow(Base):
    __tablename__ = "health_signals"
    __table_args__ = (
        CheckConstraint(
            "extraction_confidence >= 0 AND extraction_confidence <= 1",
            name="ck_signal_confidence_range",
        ),
        CheckConstraint(
            "quality_flag IN ('clean', 'low_confidence', 'requires_review', 'partial')",
            name="ck_signal_quality_flag",
        ),
        {"schema": "processing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    raw_context_event_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False
    )

    signal_type: Mapped[str] = mapped_column(Text(), nullable=False)
    signal_value: Mapped[float] = mapped_column(Float(), nullable=False)
    signal_unit: Mapped[str | None] = mapped_column(Text(), nullable=True)
    signal_direction: Mapped[str | None] = mapped_column(Text(), nullable=True)

    aggregation_method: Mapped[str | None] = mapped_column(Text(), nullable=True)
    observation_window: Mapped[str | None] = mapped_column(Text(), nullable=True)

    extraction_confidence: Mapped[float] = mapped_column(Float(), nullable=False)
    extraction_model: Mapped[str] = mapped_column(Text(), nullable=False)
    model_version: Mapped[str] = mapped_column(Text(), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(Text(), nullable=False)

    quality_flag: Mapped[str] = mapped_column(Text(), nullable=False)
    quality_metadata: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)

    captured_at_start: Mapped[datetime] = mapped_column(nullable=False)
    captured_at_end: Mapped[datetime] = mapped_column(nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(nullable=False)
    correlation_id: Mapped[str] = mapped_column(Text(), nullable=False)
    trace_id: Mapped[str] = mapped_column(Text(), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
