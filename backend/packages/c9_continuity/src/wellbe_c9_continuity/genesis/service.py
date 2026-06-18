"""Thread genesis consumer (Stories B0 + B1).

Consumes ``genesis.input_ready`` and produces exactly one durable, idempotent triage
decision per concern, then applies the corresponding side effect (Story B1):

- ``create``    — auto-open an ``active_unresolved`` C7 thread via Story A's atomic
  thread+C5-evidence invariant (only for clinically-asserted concerns).
- ``attach``    — link new evidence to the existing open thread that already covers
  the concern key (dedup precedence; never spawn a duplicate thread).
- ``candidate`` — create/update a pending candidate (the non-alarming destination
  for uncertain-but-relevant signals).
- ``no_thread`` — record a reason; no side effect.

Idempotency is claim-first: the decision row is inserted (``ON CONFLICT DO NOTHING``)
before any side effect, so the unique ``decision_inputs_hash`` is the single
serialization point. A redelivered event that does not win the insert applies NO side
effects and returns the prior record. The caller owns the commit (matching C5/C7), so
the decision, the thread/candidate, and the evidence links all land in one transaction.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from datetime import UTC

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c5_evidence.service import EvidenceService
from wellbe_c7_thread.repository import ThreadRepository
from wellbe_c7_thread.service import ThreadService
from wellbe_contracts.c5_evidence import (
    ConfidenceBasis,
    EvidenceLinkType,
    EvidenceRef,
)
from wellbe_contracts.c7_thread import HealthThreadStatus, ThreadCreatedBy
from wellbe_contracts.genesis import (
    GENESIS_POLICY_VERSION,
    ConcernKey,
    GenesisDecision,
    GenesisDecisionRecord,
    GenesisFactInput,
    GenesisInputReadyPayload,
)

from wellbe_c9_continuity.genesis.candidate_service import GenesisCandidateService
from wellbe_c9_continuity.genesis.concern_key import (
    calm_display_title,
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
        self._threads = ThreadService(session)
        self._thread_repo = ThreadRepository(session)
        self._candidates = GenesisCandidateService(session)
        self._evidence = EvidenceService(session)

    async def handle_input_ready(
        self, payload: GenesisInputReadyPayload
    ) -> list[GenesisDecisionRecord]:
        """Process a genesis.input_ready event into durable decisions + side effects.

        Facts are grouped by their derived concern key, so repeated mentions of one
        concern in a single capture collapse into one decision/outcome (its
        ``fact_ids`` lists them all) rather than fragmenting. Each decision is
        appended idempotently; redelivery of the same genesis event re-applies no
        side effects and the prior record is returned with ``idempotent_replay=True``.
        """
        groups = self._group_by_concern_key(payload)
        records: list[GenesisDecisionRecord] = []
        for concern_key, facts in groups.values():
            records.append(await self._route(payload, concern_key, facts))
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

    async def _route(
        self,
        payload: GenesisInputReadyPayload,
        concern_key: ConcernKey,
        facts: list[GenesisFactInput],
    ) -> GenesisDecisionRecord:
        intent, reason_code, confidence = classify_concern_group(facts)
        inputs_hash = decision_inputs_hash(
            concern_key=concern_key,
            source_event_id=payload.source_event_id,
            policy_version=GENESIS_POLICY_VERSION,
        )
        concern_key_json = concern_key.model_dump(mode="json")
        graph_node_id = next(
            (f.graph_node_id for f in facts if f.graph_node_id is not None), None
        )
        graph_cluster_id = next(
            (f.graph_cluster_id for f in facts if f.graph_cluster_id is not None), None
        )

        # Dedup precedence (read-only): an existing open thread for this concern key
        # always wins — both a would-be create and a would-be candidate downgrade to
        # an attach so we never spawn a duplicate thread (concern-resolution-key §4).
        existing_thread = None
        if intent in (
            GenesisDecision.CREATE_NEW_THREAD,
            GenesisDecision.CREATE_OR_UPDATE_PENDING_CANDIDATE,
        ):
            existing_thread = await self._thread_repo.find_open_thread_by_concern_key(
                patient_id=payload.patient_id, concern_key=concern_key_json
            )
        final_decision = (
            GenesisDecision.ATTACH_TO_EXISTING_THREAD
            if existing_thread is not None
            else intent
        )
        if existing_thread is not None:
            reason_code = "dedup_attach_existing_thread"

        # Claim-first idempotency: insert the decision (outcomes empty) before any
        # side effect. If we do not win the insert, a prior delivery already applied
        # the side effects — return that record and do nothing else.
        decision_id = uuid.uuid4()
        inserted_id = await self._repo.insert_decision(
            decision_id=decision_id,
            user_id=payload.patient_id,
            source_event_id=payload.source_event_id,
            capture_id=payload.capture_id,
            fact_ids=[f.fact_id for f in facts],
            graph_node_id=graph_node_id,
            graph_cluster_id=graph_cluster_id,
            concern_key=concern_key_json,
            episode_bucket=concern_key.episode_bucket,
            decision=final_decision.value,
            reason_code=reason_code,
            confidence=confidence,
            policy_version=GENESIS_POLICY_VERSION,
            decision_inputs_hash=inputs_hash,
        )
        if inserted_id is None:
            row = await self._repo.get_by_hash(inputs_hash)
            assert row is not None  # conflict guarantees a prior row
            return self._record_from_row(row, idempotent_replay=True)

        await self._apply_side_effect(
            decision_id=decision_id,
            decision=final_decision,
            payload=payload,
            concern_key=concern_key,
            concern_key_json=concern_key_json,
            facts=facts,
            confidence=confidence,
            reason_code=reason_code,
            existing_thread_id=existing_thread.id if existing_thread else None,
        )

        row = await self._repo.get_by_hash(inputs_hash)
        assert row is not None
        return self._record_from_row(row, idempotent_replay=False)

    async def _apply_side_effect(
        self,
        *,
        decision_id: uuid.UUID,
        decision: GenesisDecision,
        payload: GenesisInputReadyPayload,
        concern_key: ConcernKey,
        concern_key_json: dict[str, object],
        facts: list[GenesisFactInput],
        confidence: float | None,
        reason_code: str,
        existing_thread_id: uuid.UUID | None,
    ) -> None:
        if decision is GenesisDecision.NO_THREAD_WITH_REASON:
            return

        if decision is GenesisDecision.ATTACH_TO_EXISTING_THREAD:
            assert existing_thread_id is not None
            link_ids = await self._evidence.link_thread(
                thread_id=existing_thread_id,
                patient_id=payload.patient_id,
                evidence_refs=self._evidence_refs(facts, confidence),
                correlation_id=payload.correlation_id,
                trace_id=payload.trace_id,
            )
            await self._repo.update_decision_outcome(
                decision_id=decision_id,
                target_thread_id=existing_thread_id,
                evidence_link_ids=link_ids,
            )
            return

        if decision is GenesisDecision.CREATE_NEW_THREAD:
            created_thread_id = await self._threads.create_thread(
                patient_id=payload.patient_id,
                title=calm_display_title(facts),
                created_by=ThreadCreatedBy.SYSTEM,
                initial_status=HealthThreadStatus.ACTIVE_UNRESOLVED,
                created_via="genesis",
                genesis_reason=reason_code,
                concern_key=concern_key_json,
                evidence_refs=self._evidence_refs(facts, confidence),
                correlation_id=payload.correlation_id,
                trace_id=payload.trace_id,
            )
            await self._repo.update_decision_outcome(
                decision_id=decision_id,
                target_thread_id=created_thread_id,
                created_thread_id=created_thread_id,
            )
            return

        # CREATE_OR_UPDATE_PENDING_CANDIDATE
        candidate = await self._candidates.create_or_update(
            concern_key=concern_key,
            facts=facts,
            source_capture_ids=[payload.capture_id],
            confidence=confidence,
            reason_code=reason_code,
        )
        await self._repo.update_decision_outcome(
            decision_id=decision_id,
            candidate_id=candidate.candidate_id,
        )

    @staticmethod
    def _evidence_refs(
        facts: list[GenesisFactInput], confidence: float | None
    ) -> list[EvidenceRef]:
        """Originating evidence for the thread: one ref per source raw event.

        Deduplicated on ``raw_context_event_id`` so multiple facts from the same
        capture event produce a single primary link.
        """
        refs: dict[uuid.UUID, EvidenceRef] = {}
        for fact in facts:
            raw_id = fact.raw_context_event_id
            if raw_id in refs:
                continue
            refs[raw_id] = EvidenceRef(
                raw_context_event_id=raw_id,
                link_type=EvidenceLinkType.PRIMARY,
                confidence=fact.extraction_confidence,
                confidence_basis=ConfidenceBasis.EXTRACTION_MODEL,
            )
        return list(refs.values())

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
