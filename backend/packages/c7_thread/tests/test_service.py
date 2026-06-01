from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from wellbe_c7_thread.errors import (
    ClosureSafetyError,
    InvalidTransitionError,
    ThreadNotFoundError,
    VersionConflictError,
)
from wellbe_c7_thread.repository import ThreadRepository
from wellbe_c7_thread.service import ThreadService
from wellbe_contracts.c7_thread import (
    HealthThreadStatus,
    ThreadActor,
    ThreadActorType,
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
