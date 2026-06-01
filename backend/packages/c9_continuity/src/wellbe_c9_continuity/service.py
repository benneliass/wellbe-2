from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c7_thread.errors import (
    ClosureSafetyError,
    InvalidTransitionError,
    ThreadNotFoundError,
    VersionConflictError,
)
from wellbe_c7_thread.service import ThreadService
from wellbe_contracts.c7_thread import (
    HealthThreadStatus,
    ThreadActor,
    ThreadActorType,
    ThreadEvidenceRef,
    ThreadStateChangedPayload,
    TransitionGuardContext,
)
from wellbe_contracts.c9_continuity import (
    C9_PENDING_ITEM_CREATED,
    C9_PENDING_ITEM_DUE,
    C9_THREAD_TRANSITION_ACCEPTED,
    C9_TIMER_NO_OP_C7_REJECTED,
    C9_TIMER_NO_OP_STALE,
    DuePrecision,
    PendingItemStatus,
    PendingItemType,
    SymptomsPersistState,
    TimerActionType,
    TimerFireResult,
    workflow_id,
)
from wellbe_events import emit_event

from wellbe_c9_continuity.errors import (
    OutOfOrderThreadEventError,
    PendingItemNotFoundError,
)
from wellbe_c9_continuity.repository import ContinuityRepository

# Closure-like target statuses. C9 never requests these on the basis of a single
# normal test, and never while a blocking safety-net item is active.
_CLOSURE_LIKE = {HealthThreadStatus.CLOSED, HealthThreadStatus.EXPLAINED}


class ContinuityService:
    """C9: durable pending-item ledger + race-safe interaction with C7.

    C7 is the only thread-lifecycle authority. C9 consumes thread.state_changed,
    keeps a ledger, and requests transitions only through C7 transition_thread with
    guard metadata. A stale/guard rejection is a terminal no-op for the timer epoch.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ContinuityRepository(session)
        self._threads = ThreadService(session)

    async def create_pending_item(
        self,
        *,
        patient_id: uuid.UUID,
        primary_thread_id: uuid.UUID,
        item_type: PendingItemType,
        title: str,
        status: PendingItemStatus = PendingItemStatus.ACTIVE,
        due_at: datetime | None = None,
        due_precision: DuePrecision = DuePrecision.UNKNOWN,
        source_ref: dict | None = None,
        evidence_refs: list | None = None,
        blocks_c9_closure_request: bool = False,
        normal_test_safety_net: bool = False,
        symptoms_persist_state: SymptomsPersistState = SymptomsPersistState.UNKNOWN,
        latest_observed_thread_status_version: int | None = None,
        pending_item_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
        correlation_id: str = "c9",
        trace_id: str = "c9",
    ):
        pending_item_id = pending_item_id or uuid.uuid4()
        idem = idempotency_key or f"c9:{pending_item_id}"
        # An item with no due date must use a non-timer status (ledger CHECK).
        if due_at is None and status in (
            PendingItemStatus.SCHEDULED,
            PendingItemStatus.DUE,
            PendingItemStatus.OVERDUE,
        ):
            status = PendingItemStatus.NO_DUE_DATE
        row = await self._repo.insert_pending_item(
            pending_item_id=pending_item_id,
            patient_id=patient_id,
            primary_thread_id=primary_thread_id,
            item_type=item_type,
            status=status,
            title=title,
            idempotency_key=idem,
            due_at=due_at,
            due_precision=due_precision,
            source_ref=source_ref,
            evidence_refs=evidence_refs,
            blocks_c9_closure_request=blocks_c9_closure_request,
            normal_test_safety_net=normal_test_safety_net,
            symptoms_persist_state=symptoms_persist_state,
            latest_observed_thread_status_version=latest_observed_thread_status_version,
        )
        row.workflow_id = workflow_id(pending_item_id)
        await self._session.flush()
        await emit_event(
            session=self._session,
            event_type=C9_PENDING_ITEM_CREATED,
            payload={
                "pending_item_id": str(pending_item_id),
                "patient_id": str(patient_id),
                "thread_id": str(primary_thread_id),
                "item_type": item_type.value,
                "due_at": due_at.isoformat() if due_at else None,
                "normal_test_safety_net": normal_test_safety_net,
            },
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        return row

    async def ensure_normal_test_safety_net(
        self,
        *,
        patient_id: uuid.UUID,
        thread_id: uuid.UUID,
        status_version: int | None = None,
        evidence_refs: list | None = None,
        correlation_id: str = "c9",
        trace_id: str = "c9",
    ):
        """Create/maintain a normal-test safety-net item that blocks C9 closure.

        Used when a normal result links to an unresolved/persistent-symptom thread
        without explicit symptom-resolution evidence. The item keeps follow-up
        visible and prevents any C9 closure-like transition request.
        """
        existing = await self._repo.active_blocking_items(
            patient_id=patient_id, thread_id=thread_id
        )
        for item in existing:
            if item.normal_test_safety_net:
                return item  # already maintained
        return await self.create_pending_item(
            patient_id=patient_id,
            primary_thread_id=thread_id,
            item_type=PendingItemType.NORMAL_TEST_SAFETY_NET,
            title="Normal result with persistent symptoms — keep following up",
            status=PendingItemStatus.ACTIVE,
            blocks_c9_closure_request=True,
            normal_test_safety_net=True,
            symptoms_persist_state=SymptomsPersistState.REPORTED_PERSISTENT,
            evidence_refs=evidence_refs,
            latest_observed_thread_status_version=status_version,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

    async def reconcile_thread_state_changed(
        self,
        *,
        payload: ThreadStateChangedPayload,
        event_id: uuid.UUID,
        correlation_id: str = "c9",
        trace_id: str = "c9",
    ) -> bool:
        """Consume a thread.state_changed event idempotently and in order.

        Returns True if newly applied, False if it was a duplicate. Raises
        OutOfOrderThreadEventError if a predecessor seq has not yet been consumed.
        """
        # Ordering check before recording: predecessor must be consumed.
        latest = await self._repo.latest_consumed_seq(payload.thread_id)
        if latest is None:
            # First event for the thread must be the first transition (seq 1)
            # unless we are bootstrapping mid-stream; require seq increase only.
            pass
        elif payload.transition_seq <= latest:
            # Already at/under the high-water mark: dedupe and no-op.
            await self._repo.record_consumed_thread_event(
                event_id=event_id,
                thread_id=payload.thread_id,
                transition_seq=payload.transition_seq,
            )
            return False
        elif payload.transition_seq > latest + 1:
            raise OutOfOrderThreadEventError(
                payload.thread_id, latest + 1, payload.transition_seq
            )

        newly = await self._repo.record_consumed_thread_event(
            event_id=event_id,
            thread_id=payload.thread_id,
            transition_seq=payload.transition_seq,
        )
        if not newly:
            return False

        await self._apply_reconciliation(
            payload=payload, correlation_id=correlation_id, trace_id=trace_id
        )
        return True

    async def _apply_reconciliation(
        self,
        *,
        payload: ThreadStateChangedPayload,
        correlation_id: str,
        trace_id: str,
    ) -> None:
        meta = payload.metadata or {}
        # Safety-flagged: a normal result on a thread with persistent symptoms.
        if meta.get("normal_result_with_persistent_symptoms"):
            await self.ensure_normal_test_safety_net(
                patient_id=payload.patient_id,
                thread_id=payload.thread_id,
                status_version=payload.transition_seq + 1,
                evidence_refs=[r.model_dump(mode="json") for r in payload.evidence_refs],
                correlation_id=correlation_id,
                trace_id=trace_id,
            )

        # On closure, cancel non-applicable timers but keep history.
        if payload.to_status == HealthThreadStatus.CLOSED:
            for item in await self._repo.items_for_thread(
                patient_id=payload.patient_id, thread_id=payload.thread_id
            ):
                if (
                    item.status not in ("resolved", "cancelled", "superseded")
                    and not item.normal_test_safety_net
                ):
                    await self._repo.bump_timer_epoch(row=item)
                    await self._repo.set_status(
                        row=item, status=PendingItemStatus.CANCELLED
                    )

        # Update last-observed thread context on all active items (stale guard).
        for item in await self._repo.items_for_thread(
            patient_id=payload.patient_id, thread_id=payload.thread_id
        ):
            item.latest_observed_thread_transition_seq = payload.transition_seq
            item.latest_observed_thread_status_version = payload.transition_seq + 1
        await self._session.flush()

    async def fire_timer(
        self,
        *,
        pending_item_id: uuid.UUID,
        timer_epoch: int,
        requested_target_status: HealthThreadStatus | None = None,
        guard_context: TransitionGuardContext | None = None,
        correlation_id: str = "c9",
        trace_id: str = "c9",
    ) -> TimerFireResult:
        """Race-safe timer-fire protocol (called from a Temporal activity).

        Re-reads the ledger FOR UPDATE, rejects stale epochs as no-ops, and only
        requests a C7 transition through transition_thread with guard metadata. A
        C7 stale/guard rejection is a terminal no-op for this timer epoch.
        """
        row = await self._repo.get_for_update(pending_item_id)
        if row is None:
            raise PendingItemNotFoundError(pending_item_id)

        # Stale: superseded epoch or already terminal.
        if timer_epoch != row.timer_epoch or row.status in (
            "resolved",
            "cancelled",
            "superseded",
        ):
            await self._repo.record_timer_action(
                pending_item_id=pending_item_id,
                patient_id=row.patient_id,
                timer_epoch=timer_epoch,
                action_type=TimerActionType.NO_OP_STALE,
            )
            await self._emit(
                C9_TIMER_NO_OP_STALE, row, correlation_id, trace_id,
                extra={"timer_epoch": timer_epoch},
            )
            return TimerFireResult(
                pending_item_id=pending_item_id,
                timer_epoch=timer_epoch,
                action=TimerActionType.NO_OP_STALE,
            )

        await self._repo.record_timer_action(
            pending_item_id=pending_item_id,
            patient_id=row.patient_id,
            timer_epoch=timer_epoch,
            action_type=TimerActionType.FIRED,
        )
        await self._repo.set_status(row=row, status=PendingItemStatus.DUE)
        await self._emit(C9_PENDING_ITEM_DUE, row, correlation_id, trace_id)

        if requested_target_status is None:
            return TimerFireResult(
                pending_item_id=pending_item_id,
                timer_epoch=timer_epoch,
                action=TimerActionType.FIRED,
            )

        # C9 closure-safety layer: never request closure while a blocking
        # safety-net item is active.
        if requested_target_status in _CLOSURE_LIKE:
            blocking = await self._repo.active_blocking_items(
                patient_id=row.patient_id, thread_id=row.primary_thread_id
            )
            if blocking:
                await self._repo.record_timer_action(
                    pending_item_id=pending_item_id,
                    patient_id=row.patient_id,
                    timer_epoch=timer_epoch,
                    action_type=TimerActionType.NO_OP_STALE,
                    payload={"reason": "blocked_by_safety_net"},
                )
                return TimerFireResult(
                    pending_item_id=pending_item_id,
                    timer_epoch=timer_epoch,
                    action=TimerActionType.NO_OP_STALE,
                )

        return await self._request_transition(
            row=row,
            timer_epoch=timer_epoch,
            target_status=requested_target_status,
            guard_context=guard_context or TransitionGuardContext(),
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

    async def _request_transition(
        self,
        *,
        row,
        timer_epoch: int,
        target_status: HealthThreadStatus,
        guard_context: TransitionGuardContext,
        correlation_id: str,
        trace_id: str,
    ) -> TimerFireResult:
        idem = (
            f"c9:pending:{row.pending_item_id}:epoch:{timer_epoch}:"
            f"transition:{target_status.value}"
        )
        await self._repo.record_timer_action(
            pending_item_id=row.pending_item_id,
            patient_id=row.patient_id,
            timer_epoch=timer_epoch,
            action_type=TimerActionType.C7_TRANSITION_REQUESTED,
            payload={"target_status": target_status.value},
        )
        try:
            result = await self._threads.transition_thread(
                thread_id=row.primary_thread_id,
                target_status=target_status,
                actor=ThreadActor(type=ThreadActorType.WORKFLOW),
                reason_code="c9_timer_fired",
                idempotency_key=idem,
                correlation_id=correlation_id,
                trace_id=trace_id,
                evidence_refs=[
                    ThreadEvidenceRef(type="c9_pending_item", id=row.pending_item_id)
                ],
                guard_context=guard_context,
                expected_version=row.latest_observed_thread_status_version,
            )
        except (VersionConflictError, InvalidTransitionError, ClosureSafetyError) as exc:
            code = type(exc).__name__
            await self._repo.record_timer_action(
                pending_item_id=row.pending_item_id,
                patient_id=row.patient_id,
                timer_epoch=timer_epoch,
                action_type=TimerActionType.NO_OP_C7_REJECTED,
                c7_rejection_code=code,
            )
            await self._emit(
                C9_TIMER_NO_OP_C7_REJECTED, row, correlation_id, trace_id,
                extra={"rejection_code": code},
            )
            return TimerFireResult(
                pending_item_id=row.pending_item_id,
                timer_epoch=timer_epoch,
                action=TimerActionType.NO_OP_C7_REJECTED,
                c7_rejection_code=code,
            )
        except ThreadNotFoundError:
            await self._repo.record_timer_action(
                pending_item_id=row.pending_item_id,
                patient_id=row.patient_id,
                timer_epoch=timer_epoch,
                action_type=TimerActionType.NO_OP_C7_REJECTED,
                c7_rejection_code="ThreadNotFoundError",
            )
            return TimerFireResult(
                pending_item_id=row.pending_item_id,
                timer_epoch=timer_epoch,
                action=TimerActionType.NO_OP_C7_REJECTED,
                c7_rejection_code="ThreadNotFoundError",
            )

        await self._repo.record_timer_action(
            pending_item_id=row.pending_item_id,
            patient_id=row.patient_id,
            timer_epoch=timer_epoch,
            action_type=TimerActionType.C7_TRANSITION_ACCEPTED,
            c7_transition_id=result.event_id,
        )
        await self._emit(
            C9_THREAD_TRANSITION_ACCEPTED, row, correlation_id, trace_id,
            extra={"to_status": target_status.value},
        )
        return TimerFireResult(
            pending_item_id=row.pending_item_id,
            timer_epoch=timer_epoch,
            action=TimerActionType.C7_TRANSITION_ACCEPTED,
            c7_transition_id=result.event_id,
        )

    async def _emit(
        self, event_type: str, row, correlation_id: str, trace_id: str, extra=None
    ) -> None:
        payload = {
            "pending_item_id": str(row.pending_item_id),
            "patient_id": str(row.patient_id),
            "thread_id": str(row.primary_thread_id),
        }
        if extra:
            payload.update(extra)
        await emit_event(
            session=self._session,
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


def utcnow() -> datetime:
    return datetime.now(UTC)
