from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from wellbe_c14_investigation.errors import (
    ClosureBlockedByThreadError,
    InvestigationVersionConflictError,
)
from wellbe_c14_investigation.repository import InvestigationRepository
from wellbe_c14_investigation.service import InvestigationService
from wellbe_contracts.c7_thread import HealthThreadStatus, ThreadClosureSnapshot
from wellbe_contracts.c14_investigation import (
    InvestigationOwnerType,
    InvestigationSafetyFlag,
    InvestigationStatus,
    SafetyFlagSeverity,
    ThreadRelationship,
)


def _row(*, status="open", version=1):
    return SimpleNamespace(
        id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        status=status,
        status_version=version,
        safety_flags=[],
    )


@pytest.fixture
def service():
    svc = InvestigationService(AsyncMock(), AsyncMock())
    svc._repo = AsyncMock(spec=InvestigationRepository)
    return svc


def _snap(resolved: bool) -> ThreadClosureSnapshot:
    return ThreadClosureSnapshot(
        thread_id=uuid.uuid4(),
        status=HealthThreadStatus.EXPLAINED if resolved else HealthThreadStatus.ACTIVE_UNRESOLVED,
        status_version=2,
        is_resolved=resolved,
    )


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_writes_projection_node_and_emits(self, service):
        node_id = uuid.uuid4()
        service._repo.create.return_value = None
        service._repo.create_projection_node.return_value = node_id

        with patch(
            "wellbe_c14_investigation.service.emit_event",
            new=AsyncMock(return_value=uuid.uuid4()),
        ) as emit:
            iid = await service.create_investigation(
                patient_id=uuid.uuid4(),
                primary_question="Why am I dizzy?",
                owner_type=InvestigationOwnerType.USER,
                correlation_id="c",
                trace_id="t",
            )

        assert isinstance(iid, uuid.UUID)
        service._repo.create_projection_node.assert_awaited_once()
        service._repo.set_projection_node.assert_awaited_once_with(iid, node_id)
        emit.assert_awaited_once()


class TestTransition:
    @pytest.mark.asyncio
    async def test_valid_workflow_transition(self, service):
        row = _row(status="open", version=1)
        service._repo.find_transition_by_idempotency.return_value = None
        service._repo.get_for_update.return_value = row
        service._repo.next_transition_seq.return_value = 1
        service._repo.update_status.return_value = 1

        with patch(
            "wellbe_c14_investigation.service.emit_event",
            new=AsyncMock(return_value=uuid.uuid4()),
        ) as emit:
            result = await service.transition(
                investigation_id=row.id,
                target_status=InvestigationStatus.WAITING_FOR_DATA,
                reason_code="need_labs",
                idempotency_key="k1",
                correlation_id="c",
                trace_id="t",
            )
        assert result.to_status is InvestigationStatus.WAITING_FOR_DATA
        assert result.status_version == 2
        emit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_denied_when_thread_unresolved(self, service):
        row = _row(status="ready_for_visit", version=2)
        service._repo.find_transition_by_idempotency.return_value = None
        service._repo.get_for_update.return_value = row
        service._repo.get_linked_threads.return_value = [(uuid.uuid4(), "primary")]
        service._threads.get_closure_snapshot = AsyncMock(return_value=_snap(False))

        with patch(
            "wellbe_c14_investigation.service.emit_event", new=AsyncMock()
        ) as emit, pytest.raises(ClosureBlockedByThreadError):
            await service.transition(
                investigation_id=row.id,
                target_status=InvestigationStatus.CLOSED,
                reason_code="close",
                idempotency_key="k1",
                correlation_id="c",
                trace_id="t",
            )
        emit.assert_not_awaited()
        service._repo.update_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_close_allowed_when_threads_resolved_emits_closed(self, service):
        row = _row(status="ready_for_visit", version=2)
        service._repo.find_transition_by_idempotency.return_value = None
        service._repo.get_for_update.return_value = row
        service._repo.get_linked_threads.return_value = [(uuid.uuid4(), "primary")]
        service._repo.next_transition_seq.return_value = 3
        service._repo.update_status.return_value = 1
        service._threads.get_closure_snapshot = AsyncMock(return_value=_snap(True))

        with patch(
            "wellbe_c14_investigation.service.emit_event",
            new=AsyncMock(return_value=uuid.uuid4()),
        ) as emit:
            result = await service.transition(
                investigation_id=row.id,
                target_status=InvestigationStatus.CLOSED,
                reason_code="resolved",
                idempotency_key="k1",
                correlation_id="c",
                trace_id="t",
            )
        assert result.to_status is InvestigationStatus.CLOSED
        # state_changed + closed events
        assert emit.await_count == 2

    @pytest.mark.asyncio
    async def test_idempotent_replay(self, service):
        existing = SimpleNamespace(
            from_status="open",
            to_status="monitoring",
            transition_seq=1,
            event_id=uuid.uuid4(),
        )
        service._repo.find_transition_by_idempotency.return_value = existing
        with patch(
            "wellbe_c14_investigation.service.emit_event", new=AsyncMock()
        ) as emit:
            result = await service.transition(
                investigation_id=uuid.uuid4(),
                target_status=InvestigationStatus.MONITORING,
                reason_code="x",
                idempotency_key="k1",
                correlation_id="c",
                trace_id="t",
            )
        assert result.idempotent_replay is True
        emit.assert_not_awaited()
        service._repo.get_for_update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_version_conflict(self, service):
        row = _row(status="open", version=5)
        service._repo.find_transition_by_idempotency.return_value = None
        service._repo.get_for_update.return_value = row
        with pytest.raises(InvestigationVersionConflictError):
            await service.transition(
                investigation_id=row.id,
                target_status=InvestigationStatus.MONITORING,
                reason_code="x",
                idempotency_key="k1",
                correlation_id="c",
                trace_id="t",
                expected_version=4,
            )


class TestSafetyFlag:
    @pytest.mark.asyncio
    async def test_raise_safety_flag_emits(self, service):
        row = _row()
        service._repo.get.return_value = row
        flag = InvestigationSafetyFlag(
            flag_type="red_flag_symptom",
            severity=SafetyFlagSeverity.URGENT,
            source="rules_engine",
            requires_thread_state="escalated",
            message_key="seek_care_now",
        )
        with patch(
            "wellbe_c14_investigation.service.emit_event",
            new=AsyncMock(return_value=uuid.uuid4()),
        ) as emit:
            await service.raise_safety_flag(
                investigation_id=row.id,
                flag=flag,
                correlation_id="c",
                trace_id="t",
            )
        service._repo.append_safety_flag.assert_awaited_once()
        emit.assert_awaited_once()


class TestLinkThread:
    @pytest.mark.asyncio
    async def test_link_thread_emits(self, service):
        row = _row()
        service._repo.get.return_value = row
        with patch(
            "wellbe_c14_investigation.service.emit_event",
            new=AsyncMock(return_value=uuid.uuid4()),
        ) as emit:
            await service.link_thread(
                investigation_id=row.id,
                thread_id=uuid.uuid4(),
                relationship=ThreadRelationship.PRIMARY,
                correlation_id="c",
                trace_id="t",
            )
        service._repo.link_thread.assert_awaited_once()
        emit.assert_awaited_once()
