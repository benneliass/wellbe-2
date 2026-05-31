"""ORM models for the SEPARATE External Evidence Graph (C16) and the patient-scoped
relevance-link bridge.

Per docs/decisions/external-evidence-graph-separation.md (WEL-130):
  * external_kg.* holds external medical knowledge — NO patient_id, never personal fact.
  * external_bridge.relevance_links is the ONLY personal<->external connection; it is
    patient-scoped, RLS-protected, and always context_only.
These tables live in dedicated schemas owned by the wellbe_external role so the
personal-graph role (wellbe_graph) cannot read or write external data.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Numeric, SmallInteger, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from wellbe_db import Base

SOURCE_QUALITY_TIERS = (1, 2, 3, 4, 5)


class ExternalEvidenceSourceRow(Base):
    __tablename__ = "external_evidence_sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('clinical_guideline','official_body','systematic_review',"
            "'peer_reviewed_paper','case_report','early_research','medical_blog',"
            "'expert_explainer','forum_post','anecdote','social_post')",
            name="ck_external_source_type",
        ),
        CheckConstraint(
            "source_quality_tier BETWEEN 1 AND 5",
            name="ck_external_source_quality_tier",
        ),
        {"schema": "external_kg"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(Text(), nullable=False)
    source_quality_tier: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    tier_reason: Mapped[str] = mapped_column(Text(), nullable=False)
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    citation_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    doi: Mapped[str | None] = mapped_column(Text(), nullable=True)
    publisher: Mapped[str | None] = mapped_column(Text(), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    version_label: Mapped[str | None] = mapped_column(Text(), nullable=True)
    retraction_status: Mapped[str] = mapped_column(Text(), nullable=False, default="not_retracted")
    assigned_by: Mapped[str] = mapped_column(Text(), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(nullable=False)
    source_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)


class RelevanceLinkRow(Base):
    """The ONLY connection between a personal fact and an external source.

    Context-only by construction: ``context_only`` is CHECK-pinned TRUE, and the
    ``relevance_link`` edge_type is the only value permitted. Tenant isolation is
    enforced by RLS (app.patient_id) plus a DB trigger asserting the personal node
    belongs to the same patient.
    """

    __tablename__ = "relevance_links"
    __table_args__ = (
        CheckConstraint("edge_type = 'relevance_link'", name="ck_relevance_edge_type"),
        CheckConstraint(
            "relevance_score >= 0 AND relevance_score <= 1",
            name="ck_relevance_score_range",
        ),
        CheckConstraint(
            "source_quality_tier_snapshot BETWEEN 1 AND 5",
            name="ck_relevance_tier_snapshot",
        ),
        CheckConstraint("context_only IS TRUE", name="ck_relevance_context_only"),
        UniqueConstraint(
            "patient_id", "personal_node_id", "external_source_id", "external_claim_id",
            name="relevance_links_patient_id_personal_node_id_external_sou_key",
        ),
        {"schema": "external_bridge"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    personal_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph.kg_nodes.id"), nullable=False
    )
    thread_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    external_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("external_kg.external_evidence_sources.id"),
        nullable=False,
    )
    external_claim_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    edge_type: Mapped[str] = mapped_column(Text(), nullable=False, default="relevance_link")
    relevance_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    relevance_score_version: Mapped[str] = mapped_column(Text(), nullable=False)
    relevance_inputs: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    source_quality_tier_snapshot: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    context_only: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    created_by_actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_under_grant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
