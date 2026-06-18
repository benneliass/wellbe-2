"""Thread genesis consumer (Story B0 skeleton).

Consumes ``genesis.input_ready`` and records exactly one durable, idempotent triage
decision per concern. B0 records decisions only — the high-confidence auto-create
side effects (C7 thread create, C9 candidate create/update, C5 evidence linking)
are layered onto this same consumer in Story B1, applied idempotently downstream of
the decision record.

The caller owns the commit (matching C5/C7), so a decision and any future side
effects land in one transaction.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from datetime import UTC

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_contracts.genesis import (
    GENESIS_POLICY_VERSION,
    ConcernKey,
    GenesisDecision,
    GenesisDecisionRecord,
    GenesisFactInput,
    GenesisInputReadyPayload,
)

from wellbe_c9_continuity.genesis.concern_key import (
    classify_concern_group,
    decision_inputs_hash,
    derive_concern_key,
)
from wellbe_c9_continuity.genesis.models import GenesisDecisionRow
from wellbe_c9_continuity.genesis.repository import GenesisDecisionRepository


class ThreadGenesisService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GenesisDecisionRepository(session)

    async def handle_input_ready(
        self, payload: GenesisInputReadyPayload
    ) -> list[GenesisDecisionRecord]:
        """Process a genesis.input_ready event into durable triage decisions.

        Facts are grouped by their derived concern key, so repeated mentions of one
        concern in a single capture collapse into one decision (its ``fact_ids``
        lists them all) rather than fragmenting. Each decision is appended
        idempotently; redelivery of the same genesis event is a no-op and the prior
        record is returned with ``idempotent_replay=True``.
        """
        groups = self._group_by_concern_key(payload)

        records: list[GenesisDecisionRecord] = []
        for concern_key, facts in groups.values():
            records.append(await self._record_decision(payload, concern_key, facts))
        return records

    def _group_by_concern_key(
        self, payload: GenesisInputReadyPayload
    ) -> OrderedDict[tuple[object, ...], tuple[ConcernKey, list[GenesisFactInput]]]:
        groups: OrderedDict[
            tuple[object, ...], tuple[ConcernKey, list[GenesisFactInput]]
        ] = OrderedDict()
        for fact in payload.facts:
            key = derive_concern_key(
                user_id=payload.patient_id,
                fact=fact,
                captured_at=payload.captured_at,
            )
            dedup = (
                key.concern_type.value,
                key.normalized_concept_id,
                key.body_site,
                key.laterality,
                key.episode_bucket,
                key.source_context_class.value,
            )
            if dedup not in groups:
                groups[dedup] = (key, [])
            groups[dedup][1].append(fact)
        return groups

    async def _record_decision(
        self,
        payload: GenesisInputReadyPayload,
        concern_key: ConcernKey,
        facts: list[GenesisFactInput],
    ) -> GenesisDecisionRecord:
        decision, reason_code, confidence = classify_concern_group(facts)
        inputs_hash = decision_inputs_hash(
            concern_key=concern_key,
            source_event_id=payload.source_event_id,
            policy_version=GENESIS_POLICY_VERSION,
        )
        graph_node_id = next(
            (f.graph_node_id for f in facts if f.graph_node_id is not None), None
        )
        graph_cluster_id = next(
            (f.graph_cluster_id for f in facts if f.graph_cluster_id is not None), None
        )

        inserted_id = await self._repo.insert_decision(
            decision_id=uuid.uuid4(),
            user_id=payload.patient_id,
            source_event_id=payload.source_event_id,
            capture_id=payload.capture_id,
            fact_ids=[f.fact_id for f in facts],
            graph_node_id=graph_node_id,
            graph_cluster_id=graph_cluster_id,
            concern_key=concern_key.model_dump(mode="json"),
            episode_bucket=concern_key.episode_bucket,
            decision=decision.value,
            reason_code=reason_code,
            confidence=confidence,
            policy_version=GENESIS_POLICY_VERSION,
            decision_inputs_hash=inputs_hash,
        )

        # The row exists either way (just inserted, or a prior identical decision).
        row = await self._repo.get_by_hash(inputs_hash)
        assert row is not None  # invariant: insert-or-conflict guarantees a row
        return self._record_from_row(row, idempotent_replay=inserted_id is None)

    @staticmethod
    def _record_from_row(
        row: GenesisDecisionRow, *, idempotent_replay: bool
    ) -> GenesisDecisionRecord:
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return GenesisDecisionRecord(
            decision_id=row.decision_id,
            user_id=row.user_id,
            source_event_id=row.source_event_id,
            capture_id=row.capture_id,
            fact_ids=list(row.fact_ids or []),
            graph_node_id=row.graph_node_id,
            graph_cluster_id=row.graph_cluster_id,
            concern_key=dict(row.concern_key or {}),
            episode_bucket=row.episode_bucket,
            decision=GenesisDecision(row.decision),
            reason_code=row.reason_code,
            confidence=row.confidence,
            policy_version=row.policy_version,
            target_thread_id=row.target_thread_id,
            candidate_id=row.candidate_id,
            created_thread_id=row.created_thread_id,
            evidence_link_ids=list(row.evidence_link_ids or []),
            decision_inputs_hash=row.decision_inputs_hash,
            created_at=created_at,
            supersedes_decision_id=row.supersedes_decision_id,
            idempotent_replay=idempotent_replay,
        )
