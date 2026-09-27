"""C12 in-app notifications derived from C9 pending-item events.

In-app only (owner decision): no push, email, or messaging channel. C12 owns the
copy. Copy is calm and non-diagnostic — it names the follow-up the user is
already carrying ("Waiting for a result: Ferritin") and suggests a next step,
never an interpretation.

Every notification carries an idempotency key derived from the pending item and
its timer epoch, so a redelivered or re-emitted outbox event never produces a
second notification for the same reminder.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import DateTime, Text, func, select, update
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from wellbe_contracts.c9_continuity import (
    C9_PENDING_ITEM_CREATED,
    C9_PENDING_ITEM_DUE,
    C9_PENDING_ITEM_OVERDUE,
    PendingItemStatus,
    PendingItemType,
)
from wellbe_contracts.c12_audit import InAppNotificationKind
from wellbe_db import Base

PENDING_ITEM_EVENT_KINDS: dict[str, InAppNotificationKind] = {
    C9_PENDING_ITEM_CREATED: InAppNotificationKind.PENDING_ITEM_CREATED,
    C9_PENDING_ITEM_DUE: InAppNotificationKind.PENDING_ITEM_DUE,
    C9_PENDING_ITEM_OVERDUE: InAppNotificationKind.PENDING_ITEM_OVERDUE,
}

_TERMINAL = {
    PendingItemStatus.RESOLVED.value,
    PendingItemStatus.CANCELLED.value,
    PendingItemStatus.SUPERSEDED.value,
}
_MAX_TITLE = 200


class NotificationRow(Base):
    __tablename__ = "in_app_notifications"
    __table_args__ = ({"schema": "notifications"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(Text(), nullable=False)
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    # FK to c9.pending_items (ON DELETE CASCADE) lives in the migration only, so
    # this model does not require the C9 tables in the same ORM metadata.
    pending_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    thread_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


@dataclass(frozen=True)
class PendingItemSnapshot:
    """The C9 ledger fields C12 needs to word a reminder (read at consume time)."""

    pending_item_id: uuid.UUID
    patient_id: uuid.UUID
    thread_id: uuid.UUID
    item_type: str
    status: str
    title: str
    due_at: datetime | None


@dataclass(frozen=True)
class NotificationDraft:
    patient_id: uuid.UUID
    kind: InAppNotificationKind
    title: str
    body: str
    pending_item_id: uuid.UUID
    thread_id: uuid.UUID
    idempotency_key: str


def _format_date(value: datetime) -> str:
    return f"{value.day} {value:%b %Y}"


def _clip(text: str) -> str:
    return text if len(text) <= _MAX_TITLE else text[: _MAX_TITLE - 1].rstrip() + "…"


def render_pending_item_copy(
    kind: InAppNotificationKind, *, item_title: str, item_type: str, due_at: datetime | None
) -> tuple[str, str]:
    """(title, body) for a pending-item notification. Calm, never diagnostic."""
    if kind == InAppNotificationKind.PENDING_ITEM_CREATED:
        body = (
            f"WellBe will check in with you here on {_format_date(due_at)}. "
            "Nothing to do right now."
            if due_at
            else "WellBe will keep this visible until it's settled. Nothing to do right now."
        )
        return _clip(f"New follow-up: {item_title}"), body
    if kind == InAppNotificationKind.PENDING_ITEM_DUE:
        if item_type == PendingItemType.RESULT_PENDING.value:
            body = (
                "If the result has come in, you can add it to the thread. If not, it may be "
                "worth checking in with whoever ordered it."
            )
        elif item_type == PendingItemType.REFERRAL_PENDING.value:
            body = (
                "If you've heard about the referral, you can add it to the thread. If not, "
                "you might check on where it stands."
            )
        else:
            body = "When you're ready, take a look and add any update to the thread."
        return _clip(f"A follow-up is due: {item_title}"), body
    return (
        _clip(f"Still open: {item_title}"),
        "This follow-up has been open a little longer than planned. There's no rush — "
        "check in when it suits you, and add any update to the thread.",
    )


def draft_for_pending_item_event(
    event_type: str, payload: dict[str, object], item: PendingItemSnapshot | None
) -> NotificationDraft | None:
    """The notification a C9 pending-item event should produce, or None.

    Reads the item's *current* state so a stale reminder is dropped: nothing for
    an item that has since been resolved/cancelled, and no "due" once the item
    has already moved on to overdue (the overdue reminder supersedes it).
    """
    kind = PENDING_ITEM_EVENT_KINDS.get(event_type)
    if kind is None or item is None or item.status in _TERMINAL:
        return None
    if (
        kind == InAppNotificationKind.PENDING_ITEM_DUE
        and item.status == PendingItemStatus.OVERDUE.value
    ):
        return None

    if kind == InAppNotificationKind.PENDING_ITEM_CREATED:
        key = f"c9:{item.pending_item_id}:created"
    else:
        epoch = payload.get("timer_epoch")
        phase = "due" if kind == InAppNotificationKind.PENDING_ITEM_DUE else "overdue"
        key = f"c9:{item.pending_item_id}:{phase}:{epoch if epoch is not None else 'na'}"

    title, body = render_pending_item_copy(
        kind, item_title=item.title, item_type=item.item_type, due_at=item.due_at
    )
    return NotificationDraft(
        patient_id=item.patient_id,
        kind=kind,
        title=title,
        body=body,
        pending_item_id=item.pending_item_id,
        thread_id=item.thread_id,
        idempotency_key=key,
    )


class NotificationStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, draft: NotificationDraft, *, source_event_id: uuid.UUID | None = None
    ) -> uuid.UUID | None:
        """Insert idempotently. Returns the new id, or None if it already existed."""
        stmt = (
            pg_insert(NotificationRow)
            .values(
                id=uuid.uuid4(),
                patient_id=draft.patient_id,
                kind=draft.kind.value,
                title=draft.title,
                body=draft.body,
                pending_item_id=draft.pending_item_id,
                thread_id=draft.thread_id,
                source_event_id=source_event_id,
                idempotency_key=draft.idempotency_key,
                created_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(NotificationRow.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_patient(
        self, patient_id: uuid.UUID, *, limit: int = 20, unread_only: bool = False
    ) -> list[NotificationRow]:
        """Unread first, then newest first."""
        stmt = select(NotificationRow).where(NotificationRow.patient_id == patient_id)
        if unread_only:
            stmt = stmt.where(NotificationRow.read_at.is_(None))
        stmt = stmt.order_by(
            NotificationRow.read_at.is_(None).desc(), NotificationRow.created_at.desc()
        ).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def unread_count(self, patient_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            NotificationRow.patient_id == patient_id, NotificationRow.read_at.is_(None)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def mark_read(
        self, patient_id: uuid.UUID, notification_id: uuid.UUID
    ) -> NotificationRow | None:
        """Mark one notification read (idempotent; keeps the first read time)."""
        await self._session.execute(
            update(NotificationRow)
            .where(
                NotificationRow.id == notification_id,
                NotificationRow.patient_id == patient_id,
                NotificationRow.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        stmt = (
            select(NotificationRow)
            .where(
                NotificationRow.id == notification_id,
                NotificationRow.patient_id == patient_id,
            )
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def mark_all_read(self, patient_id: uuid.UUID) -> int:
        result = await self._session.execute(
            update(NotificationRow)
            .where(
                NotificationRow.patient_id == patient_id,
                NotificationRow.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
            .returning(NotificationRow.id)
        )
        return len(result.scalars().all())
