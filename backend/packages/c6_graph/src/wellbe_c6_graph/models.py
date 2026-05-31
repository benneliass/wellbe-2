from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, Integer, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from wellbe_db import Base


class EdgeTypeRow(Base):
    __tablename__ = "edge_types"
    __table_args__ = (
        CheckConstraint(
            "category IN ('causal', 'correlation', 'temporal', 'therapeutic', 'adverse', 'contradiction', 'refinement')",
            name="ck_edge_type_category",
        ),
        {"schema": "graph"},
    )

    code: Mapped[str] = mapped_column(Text(), primary_key=True)
    display_name: Mapped[str] = mapped_column(Text(), nullable=False)
    category: Mapped[str] = mapped_column(Text(), nullable=False)


class KgNodeRow(Base):
    __tablename__ = "kg_nodes"
    __table_args__ = (
        CheckConstraint(
            "node_type IN ('ConditionHypothesis', 'Symptom', 'Medication', 'LabResult', 'Procedure', 'VitalSign', 'Allergy', 'Immunization', 'SocialFactor', 'FamilyHistory', 'Other')",
            name="ck_node_type",
        ),
        CheckConstraint(
            "status IN ('active', 'resolved', 'superseded', 'merged')",
            name="ck_node_status",
        ),
        {"schema": "graph"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    node_type: Mapped[str] = mapped_column(Text(), nullable=False)
    normalized_key: Mapped[str] = mapped_column(Text(), nullable=False)
    display_label: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[str] = mapped_column(Text(), nullable=False, default="active")
    thread_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    embedding_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)


class KgEdgeRow(Base):
    __tablename__ = "kg_edges"
    __table_args__ = (
        CheckConstraint(
            "potential_score >= 0 AND potential_score <= 1",
            name="ck_edge_potential_score",
        ),
        CheckConstraint(
            "from_node_id != to_node_id",
            name="ck_no_self_edges",
        ),
        {"schema": "graph"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph.kg_nodes.id"), nullable=False
    )
    to_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph.kg_nodes.id"), nullable=False
    )
    edge_type: Mapped[str] = mapped_column(
        Text(), ForeignKey("graph.edge_types.code"), nullable=False
    )
    potential_score: Mapped[float] = mapped_column(Float(), nullable=False)
    score_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    score_inputs: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    needs_rescore: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    thread_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
