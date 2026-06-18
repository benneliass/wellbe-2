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


class GenesisCandidateRow(Base):
    """Pending thread candidate — the durable "Things noticed" store (genesis schema).

    A continuity-owned object produced by the genesis capability, promotion-linked
    to C7. It is intentionally a distinct store from the C9 ``pending_items`` ledger:
    a pending_item mandates a ``primary_thread_id`` and uses follow-up/referral
    statuses, so it cannot represent a pre-thread candidate (S2a reconciliation).

    Create/update is idempotent on ``candidate_key`` (a deterministic hash of the
    concern key + episode bucket, excluding the source event), so repeated mentions
    of one concern update the same candidate. ``ck_genesis_candidate_has_source``
    enforces no-orphan candidates — every candidate traces to a capture or a fact.
    """

    __tablename__ = "thread_candidates"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'promoted', 'dismissed', 'merged', 'expired')",
            name="ck_genesis_candidate_status",
        ),
        CheckConstraint(
            "cardinality(source_capture_ids) > 0 OR cardinality(source_fact_ids) > 0",
            name="ck_genesis_candidate_has_source",
        ),
        UniqueConstraint("candidate_key", name="uq_genesis_candidate_key"),
        {"schema": "genesis"},
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    candidate_key: Mapped[str] = mapped_column(Text(), nullable=False)
    concern_key: Mapped[dict[str, object]] = mapped_column(
        JSONB(), nullable=False, default=dict
    )
    episode_bucket: Mapped[str] = mapped_column(Text(), nullable=False)
    display_title: Mapped[str] = mapped_column(Text(), nullable=False)
    candidate_type: Mapped[str] = mapped_column(Text(), nullable=False)
    source_capture_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    source_fact_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    source_graph_entity_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    evidence_link_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(Text(), nullable=False, default="pending")
    confidence: Mapped[float | None] = mapped_column(Float(), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(Text(), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(nullable=False)
    seen_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    promoted_thread_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
