from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from wellbe_c9_continuity.genesis import (
    CandidateNotFoundError,
    CandidateRepository,
    GenesisCandidateService,
    GenesisDecisionRepository,
    OrphanCandidateError,
    ThreadGenesisService,
    calm_display_title,
    candidate_key,
    classify_concern_group,
    decision_inputs_hash,
    derive_concern_key,
)
from wellbe_contracts.genesis import (
    CandidateStatus,
    ConcernType,
    GenesisDecision,
    GenesisFactInput,
    GenesisInputReadyPayload,
    GraphResolutionStatus,
    SourceContextClass,
)

_CAPTURED_AT = datetime(2026, 6, 18, 10, 0, tzinfo=UTC)


def _fact(**overrides) -> GenesisFactInput:
    base = dict(
        fact_id=uuid.uuid4(),
        raw_context_event_id=uuid.uuid4(),
        fact_type="symptom",
        entity_label="Cough",
        normalized_key="cough",
        extraction_confidence=0.8,
    )
    base.update(overrides)
    return GenesisFactInput(**base)


class TestDeriveConcernKey:
    def test_prefers_c6_resolved_concept(self):
        node = uuid.uuid4()
        key = derive_concern_key(
            user_id=uuid.uuid4(),
            fact=_fact(normalized_concept_id="c6:resp.cough", graph_node_id=node),
            captured_at=_CAPTURED_AT,
        )
        assert key.normalized_concept_id == "c6:resp.cough"
        assert key.concern_type is ConcernType.SYMPTOM
        assert key.source_context_class is SourceContextClass.SYMPTOM_MENTION

    def test_falls_back_to_normalized_key_when_no_c6(self):
        key = derive_concern_key(
            user_id=uuid.uuid4(), fact=_fact(), captured_at=_CAPTURED_AT
        )
        assert key.normalized_concept_id == "fallback:cough"

    def test_episode_bucket_prefers_event_date_over_ingestion(self):
        key = derive_concern_key(
            user_id=uuid.uuid4(),
            fact=_fact(event_date=datetime(2026, 1, 9, tzinfo=UTC)),
            captured_at=_CAPTURED_AT,
        )
        assert key.episode_bucket == "2026-01"

    def test_episode_bucket_falls_back_to_captured_at(self):
        key = derive_concern_key(
            user_id=uuid.uuid4(), fact=_fact(), captured_at=_CAPTURED_AT
        )
        assert key.episode_bucket == "2026-06"

    def test_lab_fact_maps_to_lab_abnormality(self):
        key = derive_concern_key(
            user_id=uuid.uuid4(),
            fact=_fact(fact_type="lab_result", normalized_key="ldl"),
            captured_at=_CAPTURED_AT,
        )
        assert key.concern_type is ConcernType.LAB_ABNORMALITY
        assert key.source_context_class is SourceContextClass.LAB_ABNORMALITY


class TestDecisionInputsHash:
    def test_is_deterministic(self):
        user = uuid.uuid4()
        src = uuid.uuid4()
        key = derive_concern_key(
            user_id=user, fact=_fact(), captured_at=_CAPTURED_AT
        )
        h1 = decision_inputs_hash(concern_key=key, source_event_id=src)
        h2 = decision_inputs_hash(concern_key=key, source_event_id=src)
        assert h1 == h2

    def test_changes_with_policy_version(self):
        key = derive_concern_key(
            user_id=uuid.uuid4(), fact=_fact(), captured_at=_CAPTURED_AT
        )
        src = uuid.uuid4()
        assert decision_inputs_hash(
            concern_key=key, source_event_id=src, policy_version=1
        ) != decision_inputs_hash(
            concern_key=key, source_event_id=src, policy_version=2
        )

    def test_changes_with_source_event(self):
        key = derive_concern_key(
            user_id=uuid.uuid4(), fact=_fact(), captured_at=_CAPTURED_AT
        )
        assert decision_inputs_hash(
            concern_key=key, source_event_id=uuid.uuid4()
        ) != decision_inputs_hash(concern_key=key, source_event_id=uuid.uuid4())


class TestClassifyConcernGroup:
    def test_concern_forming_defaults_to_candidate(self):
        decision, reason, confidence = classify_concern_group(
            [_fact(extraction_confidence=0.6), _fact(extraction_confidence=0.9)]
        )
        assert decision is GenesisDecision.CREATE_OR_UPDATE_PENDING_CANDIDATE
        assert reason == "default_candidate_pending_classification"
        assert confidence == 0.9

    def test_negated_only_group_is_no_thread(self):
        decision, reason, confidence = classify_concern_group(
            [_fact(is_negated=True)]
        )
        assert decision is GenesisDecision.NO_THREAD_WITH_REASON
        assert reason == "not_concern_forming"
        assert confidence is None

    def test_non_concern_fact_type_is_no_thread(self):
        decision, _, _ = classify_concern_group([_fact(fact_type="family_history")])
        assert decision is GenesisDecision.NO_THREAD_WITH_REASON


def _row(**overrides) -> SimpleNamespace:
    base = dict(
        decision_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        source_event_id=uuid.uuid4(),
        capture_id=uuid.uuid4(),
        fact_ids=[uuid.uuid4()],
        graph_node_id=None,
        graph_cluster_id=None,
        concern_key={"concern_type": "symptom"},
        episode_bucket="2026-06",
        decision="candidate",
        reason_code="default_candidate_pending_classification",
        confidence=0.8,
        policy_version=1,
        target_thread_id=None,
        candidate_id=None,
        created_thread_id=None,
        evidence_link_ids=[],
        decision_inputs_hash="hash-1",
        created_at=datetime(2026, 6, 18, 10, 0),
        supersedes_decision_id=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def service():
    svc = ThreadGenesisService(AsyncMock())
    svc._repo = AsyncMock(spec=GenesisDecisionRepository)
    return svc


def _payload(facts: list[GenesisFactInput]) -> GenesisInputReadyPayload:
    return GenesisInputReadyPayload(
        patient_id=uuid.uuid4(),
        capture_id=uuid.uuid4(),
        source_event_id=uuid.uuid4(),
        captured_at=_CAPTURED_AT,
        facts=facts,
        graph_resolution_status=GraphResolutionStatus.PARTIAL,
        correlation_id="corr-1",
        trace_id="trace-1",
    )


class TestHandleInputReady:
    @pytest.mark.asyncio
    async def test_records_one_decision_per_concern_group(self, service):
        # Two "cough" facts (same concern) + one "ldl" lab fact (distinct concern).
        facts = [
            _fact(normalized_key="cough"),
            _fact(normalized_key="cough"),
            _fact(fact_type="lab_result", normalized_key="ldl", entity_label="LDL"),
        ]
        service._repo.insert_decision.return_value = uuid.uuid4()
        service._repo.get_by_hash.side_effect = lambda h: _row(decision_inputs_hash=h)

        records = await service.handle_input_ready(_payload(facts))

        assert len(records) == 2
        assert service._repo.insert_decision.await_count == 2
        # The cough group carried both fact ids.
        cough_call = service._repo.insert_decision.await_args_list[0].kwargs
        assert len(cough_call["fact_ids"]) == 2
        assert cough_call["decision"] == GenesisDecision.CREATE_OR_UPDATE_PENDING_CANDIDATE.value

    @pytest.mark.asyncio
    async def test_redelivery_is_idempotent_replay(self, service):
        # insert returns None → the decision already existed (redelivery).
        service._repo.insert_decision.return_value = None
        service._repo.get_by_hash.side_effect = lambda h: _row(decision_inputs_hash=h)

        records = await service.handle_input_ready(_payload([_fact()]))

        assert len(records) == 1
        assert records[0].idempotent_replay is True

    @pytest.mark.asyncio
    async def test_fresh_insert_is_not_replay(self, service):
        service._repo.insert_decision.return_value = uuid.uuid4()
        service._repo.get_by_hash.side_effect = lambda h: _row(decision_inputs_hash=h)

        records = await service.handle_input_ready(_payload([_fact()]))

        assert records[0].idempotent_replay is False


class TestCandidateKey:
    def test_excludes_source_event_and_policy(self):
        # candidate_key is derived purely from the concern key, so the same concern
        # seen via two different captures dedups to one candidate.
        user = uuid.uuid4()
        k1 = derive_concern_key(user_id=user, fact=_fact(), captured_at=_CAPTURED_AT)
        k2 = derive_concern_key(user_id=user, fact=_fact(), captured_at=_CAPTURED_AT)
        assert candidate_key(k1) == candidate_key(k2)

    def test_differs_by_episode_bucket(self):
        user = uuid.uuid4()
        jan = derive_concern_key(
            user_id=user,
            fact=_fact(event_date=datetime(2026, 1, 9, tzinfo=UTC)),
            captured_at=_CAPTURED_AT,
        )
        jun = derive_concern_key(
            user_id=user, fact=_fact(), captured_at=_CAPTURED_AT
        )
        assert candidate_key(jan) != candidate_key(jun)


class TestCalmDisplayTitle:
    def test_uses_most_confident_concern_label(self):
        title = calm_display_title(
            [_fact(entity_label="cough", extraction_confidence=0.6),
             _fact(entity_label="persistent cough", extraction_confidence=0.9)]
        )
        assert title == "Persistent cough"


def _candidate_row(**overrides) -> SimpleNamespace:
    now = datetime(2026, 6, 18, 10, 0)
    base = dict(
        candidate_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        candidate_key="ckey-1",
        concern_key={"concern_type": "symptom"},
        episode_bucket="2026-06",
        display_title="Cough",
        candidate_type="symptom",
        source_capture_ids=[],
        source_fact_ids=[uuid.uuid4()],
        source_graph_entity_ids=[],
        evidence_link_ids=[],
        status="pending",
        confidence=0.8,
        reason_code=None,
        first_seen_at=now,
        last_seen_at=now,
        seen_count=1,
        promoted_thread_id=None,
        created_at=now,
        updated_at=now,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def candidate_service():
    svc = GenesisCandidateService(AsyncMock())
    svc._repo = AsyncMock(spec=CandidateRepository)
    return svc


class TestCandidateService:
    @pytest.mark.asyncio
    async def test_create_or_update_raises_on_orphan(self, candidate_service):
        key = derive_concern_key(
            user_id=uuid.uuid4(), fact=_fact(), captured_at=_CAPTURED_AT
        )
        with pytest.raises(OrphanCandidateError):
            await candidate_service.create_or_update(concern_key=key, facts=[])

    @pytest.mark.asyncio
    async def test_create_or_update_derives_title_and_returns_candidate(
        self, candidate_service
    ):
        key = derive_concern_key(
            user_id=uuid.uuid4(), fact=_fact(), captured_at=_CAPTURED_AT
        )
        candidate_service._repo.upsert.return_value = (
            _candidate_row(display_title="Cough"),
            True,
        )
        result = await candidate_service.create_or_update(
            concern_key=key, facts=[_fact(entity_label="cough")]
        )
        assert result.status is CandidateStatus.PENDING
        assert result.display_title == "Cough"
        assert candidate_service._repo.upsert.await_args.kwargs["display_title"] == "Cough"

    @pytest.mark.asyncio
    async def test_dismiss_missing_candidate_raises(self, candidate_service):
        candidate_service._repo.set_status.return_value = None
        with pytest.raises(CandidateNotFoundError):
            await candidate_service.dismiss(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_promote_sets_status_and_thread(self, candidate_service):
        thread_id = uuid.uuid4()
        candidate_service._repo.set_status.return_value = _candidate_row(
            status="promoted", promoted_thread_id=thread_id
        )
        result = await candidate_service.promote(uuid.uuid4(), thread_id=thread_id)
        assert result.status is CandidateStatus.PROMOTED
        assert result.promoted_thread_id == thread_id

    def test_promotion_due_on_repeat_signal(self):
        pending = ThreadCandidateFactory(seen_count=3)
        assert GenesisCandidateService.is_promotion_due(pending) is True

    def test_promotion_not_due_below_threshold(self):
        pending = ThreadCandidateFactory(seen_count=2)
        assert GenesisCandidateService.is_promotion_due(pending) is False

    def test_promotion_not_due_when_not_pending(self):
        promoted = ThreadCandidateFactory(seen_count=5, status=CandidateStatus.PROMOTED)
        assert GenesisCandidateService.is_promotion_due(promoted) is False


def ThreadCandidateFactory(**overrides):
    from wellbe_contracts.genesis import ThreadCandidate

    now = datetime(2026, 6, 18, 10, 0, tzinfo=UTC)
    base = dict(
        candidate_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        episode_bucket="2026-06",
        display_title="Cough",
        candidate_type=ConcernType.SYMPTOM,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    base.update(overrides)
    return ThreadCandidate(**base)
