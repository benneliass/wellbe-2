"""ORM models for C16 tables not already declared in wellbe_c6_graph.external.

``ExternalEvidenceSourceRow`` and ``RelevanceLinkRow`` live in
``wellbe_c6_graph.external`` (shared with the C6 retrofit). Here we add the
external_claims and source_quality_reviews tables.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from wellbe_db import Base


class ExternalClaimRow(Base):
    __tablename__ = "external_claims"
    __table_args__ = (
        CheckConstraint(
            "claim_kind IN ('association','risk_factor','mechanism','contraindication',"
            "'guideline_recommendation','educational_context','anecdote')",
            name="ck_external_claim_kind",
        ),
        {"schema": "external_kg"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("external_kg.external_evidence_sources.id"),
        nullable=False,
    )
    claim_text: Mapped[str] = mapped_column(Text(), nullable=False)
    claim_kind: Mapped[str] = mapped_column(Text(), nullable=False)
    population_context: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    evidence_attributes: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceQualityReviewRow(Base):
    """Auditable tier-change history. Usage can NEVER upgrade a tier."""

    __tablename__ = "source_quality_reviews"
    __table_args__ = (
        CheckConstraint("new_tier BETWEEN 1 AND 5", name="ck_source_review_new_tier"),
        {"schema": "external_kg"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("external_kg.external_evidence_sources.id"),
        nullable=False,
    )
    previous_tier: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    new_tier: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    reason: Mapped[str] = mapped_column(Text(), nullable=False)
    reviewer_actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
