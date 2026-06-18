from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from wellbe_c7_thread.errors import (
    ClosureSafetyError,
    InvalidTransitionError,
    SystemThreadRequiresEvidenceError,
    ThreadNotFoundError,
    VersionConflictError,
)
from wellbe_c7_thread.repository import ThreadRepository
from wellbe_c7_thread.service import ThreadService
from wellbe_contracts.c5_evidence import (
    ConfidenceBasis,
    EvidenceLinkType,
    EvidenceRef,
)
from wellbe_contracts.c7_thread import (
    HealthThreadStatus,
    ThreadActor,
    ThreadActorType,
    ThreadCreatedBy,
    TransitionGuardContext,
)


def _thread_row(*, status: str, version: int = 1):
    return SimpleNamespace(
        id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        title="thread",
        status=status,
        status_version=version,
        status_changed_at=None,
        created_at=None,
    )


@pytest.fixture
def service():
    svc = ThreadService(AsyncMock())
    svc._repo = AsyncMock(spec=ThreadRepository)
    return svc


def _actor() -> ThreadActor:
    return ThreadActor(type=ThreadActorType.USER, id=uuid.uuid4())


def _evidence_ref() -> EvidenceRef:
    return EvidenceRef(
        raw_context_event_id=uuid.uuid4(),
        link_type=EvidenceLinkType.PRIMARY,
        confidence=0.9,
        confidence_basis=ConfidenceBasis.EXTRACTION_MODEL,
    )


class TestCreateThread:
    @pytest.mark.asyncio
    async def test_user_create_defaults_to_draft_without_evidence(self, service):
        with patch("wellbe_c5_evidence.service.EvidenceService") as mock_es:
            tid = await service.create_thread(
                patient_id=uuid.uuid4(), title="Cough"
            )

        assert isinstance(tid, uuid.UUID)
        service._repo.create_thread.assert_awaited_once()
        kwargs = service._repo.create_thread.await_args.kwargs
        assert kwargs["status"] == HealthThreadStatus.DRAFT.value
        assert kwargs["created_by"] == ThreadCreatedBy.USER.value
        # No evidence supplied for a manual draft → C5 is never touched.
        mock_es.assert_not_called()

    @pytest.mark.asyncio
    async def test_system_create_without_evidence_raises_before_any_write(self, service):
        with pytest.raises(SystemThreadRequiresEvidenceError):
            await service.create_thread(
                patient_id=uuid.uuid4(),
                title="Cough",
                created_by=ThreadCreatedBy.SYSTEM,
                initial_status=HealthThreadStatus.ACTIVE_UNRESOLVED,
            )
        # Invariant is checked before insert: no orphan thread is ever flushed.
        service._repo.create_thread.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_system_create_writes_thread_and_links_evidence_atomically(self, service):
        ref = _evidence_ref()
        evidence_instance = AsyncMock()
        patient_id = uuid.uuid4()

        with patch(
            "wellbe_c5_evidence.service.EvidenceService",
            return_value=evidence_instance,
        ) as mock_es:
            tid = await service.create_thread(
                patient_id=patient_id,
                title="Cough",
                created_by=ThreadCreatedBy.SYSTEM,
                initial_status=HealthThreadStatus.ACTIVE_UNRESOLVED,
                created_via="continuity_triage",
                genesis_reason="explicit_user_concern",
                concern_key={"concept": "cough", "type": "symptom"},
                evidence_refs=[ref],
                correlation_id="corr-1",
                trace_id="trace-1",
            )

        # Thread row written with genesis metadata + the genesis initial status.
        kwargs = service._repo.create_thread.await_args.kwargs
        assert kwargs["status"] == HealthThreadStatus.ACTIVE_UNRESOLVED.value
        assert kwargs["created_by"] == ThreadCreatedBy.SYSTEM.value
        assert kwargs["created_via"] == "continuity_triage"
        assert kwargs["genesis_reason"] == "explicit_user_concern"
        assert kwargs["concern_key"] == {"concept": "cough", "type": "symptom"}

        # Same session passed to C5 so the writes share one transaction.
        mock_es.assert_called_once_with(service._session)
        evidence_instance.link_thread.assert_awaited_once()
        link_kwargs = evidence_instance.link_thread.await_args.kwargs
        assert link_kwargs["thread_id"] == tid
        assert link_kwargs["patient_id"] == patient_id
        assert link_kwargs["evidence_refs"] == [ref]
        assert link_kwargs["linked_by"] == "system"

    @pytest.mark.asyncio
    async def test_user_create_with_evidence_links_as_user(self, service):
        ref = _evidence_ref()
        evidence_instance = AsyncMock()

        with patch(
            "wellbe_c5_evidence.service.EvidenceService",
            return_value=evidence_instance,
        ):
            await service.create_thread(
                patient_id=uuid.uuid4(),
                title="Cough",
                created_by=ThreadCreatedBy.USER,
                evidence_refs=[ref],
            )

        evidence_instance.link_thread.assert_awaited_once()
        assert evidence_instance.link_thread.await_args.kwargs["linked_by"] == "user"


class TestTransitionThread:
    @pytest.mark.asyncio
    async def test_valid_transition_emits_event_and_increments_version(self, service):
        row = _thread_row(status="active_unresolved", version=3)
        service._repo.find_transition_by_idempotency.return_value = None
        service._repo.get_for_update.return_value = row
        service._repo.next_transition_seq.return_value = 4
        service._repo.update_status.return_value = 1
        event_id = uuid.uuid4()

        with patch(
            "wellbe_c7_thread.service.emit_event", new=AsyncMock(return_value=event_id)
        ) as mock_emit:
            result = await service.transition_thread(
                thread_id=row.id,
                target_status=HealthThreadStatus.WAITING_FOR_RESULT,
                actor=_actor(),
                reason_code="result_pending",
                idempotency_key="key-1",
                correlation_id="corr-1",
                trace_id="trace-1",
            )

        assert result.from_status is HealthThreadStatus.ACTIVE_UNRESOLVED
        assert result.to_status is HealthThreadStatus.WAITING_FOR_RESULT
        assert result.status_version == 4
        assert result.transition_seq == 4
        assert result.event_id == event_id
        assert result.idempotent_replay is False
        mock_emit.assert_awaited_once()
        service._repo.insert_transition.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_idempotent_replay_returns_prior_result_without_emit(self, service):
        existing = SimpleNamespace(
            from_status="active_unresolved",
            to_status="waiting_for_result",
            transition_seq=4,
            event_id=uuid.uuid4(),
            safety_flags=[],
        )
        service._repo.find_transition_by_idempotency.return_value = existing

        with patch(
            "wellbe_c7_thread.service.emit_event", new=AsyncMock()
        ) as mock_emit:
            result = await service.transition_thread(
                thread_id=uuid.uuid4(),
                target_status=HealthThreadStatus.WAITING_FOR_RESULT,
                actor=_actor(),
                reason_code="result_pending",
                idempotency_key="key-1",
                correlation_id="corr-1",
                trace_id="trace-1",
            )

        assert result.idempotent_replay is True
        assert result.transition_seq == 4
        mock_emit.assert_not_awaited()
        service._repo.get_for_update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_thread_raises(self, service):
        service._repo.find_transition_by_idempotency.return_value = None
        service._repo.get_for_update.return_value = None

        with pytest.raises(ThreadNotFoundError):
            await service.transition_thread(
                thread_id=uuid.uuid4(),
                target_status=HealthThreadStatus.ACTIVE_UNRESOLVED,
                actor=_actor(),
                reason_code="start",
                idempotency_key="key-1",
                correlation_id="corr-1",
                trace_id="trace-1",
            )

    @pytest.mark.asyncio
    async def test_expected_version_mismatch_raises_conflict(self, service):
        row = _thread_row(status="active_unresolved", version=5)
        service._repo.find_transition_by_idempotency.return_value = None
        service._repo.get_for_update.return_value = row

        with pytest.raises(VersionConflictError):
            await service.transition_thread(
                thread_id=row.id,
                target_status=HealthThreadStatus.WAITING_FOR_RESULT,
                actor=_actor(),
                reason_code="result_pending",
                idempotency_key="key-1",
                correlation_id="corr-1",
                trace_id="trace-1",
                expected_version=4,
            )

    @pytest.mark.asyncio
    async def test_lost_update_race_raises_conflict(self, service):
        row = _thread_row(status="active_unresolved", version=1)
        service._repo.find_transition_by_idempotency.return_value = None
        service._repo.get_for_update.return_value = row
        service._repo.next_transition_seq.return_value = 2
        service._repo.update_status.return_value = 0  # concurrent writer won

        with (
            patch(
                "wellbe_c7_thread.service.emit_event",
                new=AsyncMock(return_value=uuid.uuid4()),
            ),
            pytest.raises(VersionConflictError),
        ):
            await service.transition_thread(
                thread_id=row.id,
                target_status=HealthThreadStatus.WAITING_FOR_RESULT,
                actor=_actor(),
                reason_code="result_pending",
                idempotency_key="key-1",
                correlation_id="corr-1",
                trace_id="trace-1",
            )

    @pytest.mark.asyncio
    async def test_invalid_edge_does_not_emit(self, service):
        row = _thread_row(status="closed", version=2)
        service._repo.find_transition_by_idempotency.return_value = None
        service._repo.get_for_update.return_value = row

        with (
            patch("wellbe_c7_thread.service.emit_event", new=AsyncMock()) as mock_emit,
            pytest.raises(InvalidTransitionError),
        ):
            await service.transition_thread(
                thread_id=row.id,
                target_status=HealthThreadStatus.ACTIVE_UNRESOLVED,
                actor=_actor(),
                reason_code="bad",
                idempotency_key="key-1",
                correlation_id="corr-1",
                trace_id="trace-1",
            )
        mock_emit.assert_not_awaited()
        service._repo.update_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unsafe_closure_does_not_emit(self, service):
        row = _thread_row(status="explained", version=2)
        service._repo.find_transition_by_idempotency.return_value = None
        service._repo.get_for_update.return_value = row

        with (
            patch("wellbe_c7_thread.service.emit_event", new=AsyncMock()) as mock_emit,
            pytest.raises(ClosureSafetyError),
        ):
            await service.transition_thread(
                thread_id=row.id,
                target_status=HealthThreadStatus.CLOSED,
                actor=_actor(),
                reason_code="close",
                idempotency_key="key-1",
                correlation_id="corr-1",
                trace_id="trace-1",
                guard_context=TransitionGuardContext(symptoms_persist=True),
            )
        mock_emit.assert_not_awaited()
        service._repo.update_status.assert_not_awaited()
