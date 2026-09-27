"""C13 /v2 in-app notifications (C12).

Reminders derived from C9 pending items (a follow-up opened, came due, or is
still open). In-app only — nothing here is pushed, emailed, or messaged. Every
route is self-scoped to the caller's patient, access-checked before any read,
and audited through the outbox. A notification that is not the caller's is a
404 (existence is never disclosed).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from wellbe_c12_audit.notifications import NotificationRow, NotificationStore
from wellbe_contracts.c13_api import (
    NotificationListV2,
    NotificationsMarkedReadV2,
    NotificationV2,
    ProblemCode,
)

from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, require_access
from wellbe_api.errors import ProblemError

router = APIRouter(prefix="/v2", tags=["v2-notifications"])

_RESOURCE = "pending_item"


def _to_v2(row: NotificationRow) -> NotificationV2:
    return NotificationV2(
        notification_id=str(row.id),
        kind=row.kind,
        title=row.title,
        body=row.body,
        pending_item_id=str(row.pending_item_id) if row.pending_item_id else None,
        thread_id=str(row.thread_id) if row.thread_id else None,
        created_at=row.created_at,
        read_at=row.read_at,
    )


@router.get("/notifications", response_model=NotificationListV2)
async def list_notifications(
    principal: PrincipalDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    unread_only: Annotated[bool, Query()] = False,
) -> NotificationListV2:
    await require_access(principal, session, action="read", resource_type=_RESOURCE)
    store = NotificationStore(session)
    rows = await store.list_for_patient(
        principal.patient_id, limit=limit, unread_only=unread_only
    )
    unread = await store.unread_count(principal.patient_id)
    await audit_ref(
        session,
        event_type="c13.notifications.read",
        principal=principal,
        summary="In-app notifications read",
        extra={"count": len(rows), "unread_count": unread},
    )
    await session.commit()
    return NotificationListV2(notifications=[_to_v2(r) for r in rows], unread_count=unread)


@router.post("/notifications/read-all", response_model=NotificationsMarkedReadV2)
async def mark_all_notifications_read(
    principal: PrincipalDep, session: SessionDep
) -> NotificationsMarkedReadV2:
    await require_access(principal, session, action="write", resource_type=_RESOURCE)
    marked = await NotificationStore(session).mark_all_read(principal.patient_id)
    await audit_ref(
        session,
        event_type="c13.notifications.marked_all_read",
        principal=principal,
        summary="All in-app notifications marked read",
        extra={"marked_read": marked},
    )
    await session.commit()
    return NotificationsMarkedReadV2(marked_read=marked, unread_count=0)


@router.post("/notifications/{notification_id}/read", response_model=NotificationV2)
async def mark_notification_read(
    notification_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> NotificationV2:
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=notification_id
    )
    row = await NotificationStore(session).mark_read(principal.patient_id, notification_id)
    if row is None:
        raise ProblemError(
            status=404,
            code=ProblemCode.GRANT_REQUIRED,
            title="Notification not found",
            detail="No notification with that id is visible to the principal.",
            correlation_id=principal.correlation_id,
        )
    await audit_ref(
        session,
        event_type="c13.notification.marked_read",
        principal=principal,
        summary="In-app notification marked read",
        extra={"notification_id": str(notification_id)},
    )
    await session.commit()
    return _to_v2(row)
