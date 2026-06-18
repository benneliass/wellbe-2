from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Float, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from wellbe_db import Base


class GenesisDecisionRow(Base):
    """Append-only, idempotent triage decision ledger (genesis schema).

    One row per (concern_key, genesis event) routing decision. The
    ``decision_inputs_hash`` UNIQUE constraint makes redelivery of the same
    genesis event a no-op (insert ... ON CONFLICT DO NOTHING). An intentional
    re-evaluation under a new ``policy_version`` writes a NEW row with
    ``supersedes_decision_id`` set rather than mutating the prior row.

    This is an internal pipeline ledger written by the system genesis consumer
    (analogous to ``evidence.evidence_links``): it is never mutated and carries no
    clinical facts, so it has no row-level security — patient isolation is enforced
    at any read boundary that exposes it.
    """

    __tablename__ = "genesis_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('attach', 'create', 'candidate', 'no_thread')",
            name="ck_genesis_decision",
        ),
        UniqueConstraint("decision_inputs_hash", name="uq_genesis_decision_inputs_hash"),
        {"schema": "genesis"},
    )

    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    capture_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    fact_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    graph_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    graph_cluster_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    concern_key: Mapped[dict[str, object]] = mapped_column(
        JSONB(), nullable=False, default=dict
    )
    episode_bucket: Mapped[str] = mapped_column(Text(), nullable=False)
    decision: Mapped[str] = mapped_column(Text(), nullable=False)
    reason_code: Mapped[str] = mapped_column(Text(), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float(), nullable=True)
    policy_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    target_thread_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_thread_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    evidence_link_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    decision_inputs_hash: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    supersedes_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
