from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_contracts.c9_continuity import (
    DuePrecision,
    PendingItemStatus,
    PendingItemType,
    SymptomsPersistState,
    TimerActionType,
)

from wellbe_c9_continuity.models import (
    ConsumedThreadEventRow,
    PendingItemEventRow,
    PendingItemRow,
    TimerActionRow,
)


def _naive_utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ContinuityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_pending_item(
        self,
        *,
        pending_item_id: uuid.UUID,
        patient_id: uuid.UUID,
        primary_thread_id: uuid.UUID,
        item_type: PendingItemType,
        status: PendingItemStatus,
        title: str,
        idempotency_key: str,
        due_at: datetime | None = None,
        due_precision: DuePrecision = DuePrecision.UNKNOWN,
        source_ref: dict | None = None,
        evidence_refs: list | None = None,
        blocks_c9_closure_request: bool = False,
        normal_test_safety_net: bool = False,
        symptoms_persist_state: SymptomsPersistState = SymptomsPersistState.UNKNOWN,
        latest_observed_thread_status_version: int | None = None,
        latest_observed_thread_transition_seq: int | None = None,
    ) -> PendingItemRow:
        now = _naive_utcnow()
        row = PendingItemRow(
            pending_item_id=pending_item_id,
            patient_id=patient_id,
            primary_thread_id=primary_thread_id,
            item_type=item_type.value,
            status=status.value,
            title=title,
            due_at=due_at,
            due_precision=due_precision.value,
            source_ref=source_ref or {},
            evidence_refs=evidence_refs or [],
            blocks_c9_closure_request=blocks_c9_closure_request,
            normal_test_safety_net=normal_test_safety_net,
            symptoms_persist_state=symptoms_persist_state.value,
            latest_observed_thread_status_version=latest_observed_thread_status_version,
            latest_observed_thread_transition_seq=latest_observed_thread_transition_seq,
            timer_epoch=0,
            version=1,
            created_at=now,
            updated_at=now,
            idempotency_key=idempotency_key,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, pending_item_id: uuid.UUID) -> PendingItemRow | None:
        return await self._session.get(PendingItemRow, pending_item_id)

    async def get_for_update(self, pending_item_id: uuid.UUID) -> PendingItemRow | None:
        stmt = (
            select(PendingItemRow)
            .where(PendingItemRow.pending_item_id == pending_item_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def active_blocking_items(
        self, *, patient_id: uuid.UUID, thread_id: uuid.UUID
    ) -> list[PendingItemRow]:
        """Items that block any C9 closure request for the thread."""
        stmt = select(PendingItemRow).where(
            PendingItemRow.patient_id == patient_id,
            PendingItemRow.primary_thread_id == thread_id,
            PendingItemRow.blocks_c9_closure_request.is_(True),
            PendingItemRow.status.notin_(["resolved", "cancelled", "superseded"]),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def items_for_thread(
        self, *, patient_id: uuid.UUID, thread_id: uuid.UUID
    ) -> list[PendingItemRow]:
        stmt = select(PendingItemRow).where(
            PendingItemRow.patient_id == patient_id,
            PendingItemRow.primary_thread_id == thread_id,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def bump_timer_epoch(self, *, row: PendingItemRow) -> int:
        row.timer_epoch += 1
        row.version += 1
        row.updated_at = _naive_utcnow()
        await self._session.flush()
        return row.timer_epoch

    async def set_status(self, *, row: PendingItemRow, status: PendingItemStatus) -> None:
        row.status = status.value
        row.version += 1
        row.updated_at = _naive_utcnow()
        if status == PendingItemStatus.RESOLVED:
            row.resolved_at = _naive_utcnow()
        if status == PendingItemStatus.CANCELLED:
            row.cancelled_at = _naive_utcnow()
        await self._session.flush()

    async def record_consumed_thread_event(
        self, *, event_id: uuid.UUID, thread_id: uuid.UUID, transition_seq: int
    ) -> bool:
        """Insert into the dedup ledger. Returns False if already consumed."""
        stmt = (
            pg_insert(ConsumedThreadEventRow)
            .values(
                event_id=event_id,
                thread_id=thread_id,
                transition_seq=transition_seq,
                consumed_at=_naive_utcnow(),
            )
            .on_conflict_do_nothing(index_elements=["event_id"])
            .returning(ConsumedThreadEventRow.event_id)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none() is not None

    async def latest_consumed_seq(self, thread_id: uuid.UUID) -> int | None:
        stmt = text(
            "SELECT max(transition_seq) FROM c9.consumed_thread_events WHERE thread_id = :t"
        )
        result = await self._session.execute(stmt, {"t": str(thread_id)})
        return result.scalar_one_or_none()

    async def record_timer_action(
        self,
        *,
        pending_item_id: uuid.UUID,
        patient_id: uuid.UUID,
        timer_epoch: int,
        action_type: TimerActionType,
        c7_transition_id: uuid.UUID | None = None,
        c7_rejection_code: str | None = None,
        payload: dict | None = None,
    ) -> bool:
        """Append a timer action. Idempotent on (item, epoch, action)."""
        stmt = (
            pg_insert(TimerActionRow)
            .values(
                timer_action_id=uuid.uuid4(),
                pending_item_id=pending_item_id,
                patient_id=patient_id,
                timer_epoch=timer_epoch,
                action_type=action_type.value,
                c7_transition_id=c7_transition_id,
                c7_rejection_code=c7_rejection_code,
                payload=payload or {},
                occurred_at=_naive_utcnow(),
            )
            .on_conflict_do_nothing(
                index_elements=["pending_item_id", "timer_epoch", "action_type"]
            )
            .returning(TimerActionRow.timer_action_id)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none() is not None

    async def record_item_event(
        self,
        *,
        pending_item_id: uuid.UUID,
        patient_id: uuid.UUID,
        event_type: str,
        idempotency_key: str,
        event_payload: dict | None = None,
        actor: dict | None = None,
    ) -> None:
        stmt = (
            pg_insert(PendingItemEventRow)
            .values(
                pending_item_event_id=uuid.uuid4(),
                pending_item_id=pending_item_id,
                patient_id=patient_id,
                event_type=event_type,
                event_payload=event_payload or {},
                actor=actor or {},
                occurred_at=_naive_utcnow(),
                idempotency_key=idempotency_key,
            )
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
        )
        await self._session.execute(stmt)
        await self._session.flush()
