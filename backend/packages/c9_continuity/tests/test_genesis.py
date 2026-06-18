from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from wellbe_c9_continuity.genesis import (
    GenesisDecisionRepository,
    ThreadGenesisService,
    classify_concern_group,
    decision_inputs_hash,
    derive_concern_key,
)
from wellbe_contracts.genesis import (
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
