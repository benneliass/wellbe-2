"""C12 in-app notification drafting from C9 pending-item events."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

import pytest
from wellbe_c12_audit.notifications import (
    PendingItemSnapshot,
    draft_for_pending_item_event,
    render_pending_item_copy,
)
from wellbe_contracts.c12_audit import InAppNotificationKind

_ITEM_ID = uuid.UUID("aaaaaaaa-0000-4000-8000-000000000001")
_DUE = datetime(2026, 10, 4, 9, 30, tzinfo=UTC)


def _item(status: str = "scheduled", item_type: str = "result_pending") -> PendingItemSnapshot:
    return PendingItemSnapshot(
        pending_item_id=_ITEM_ID,
        patient_id=uuid.uuid4(),
        thread_id=uuid.uuid4(),
        item_type=item_type,
        status=status,
        title="Waiting for a result: Ferritin",
        due_at=_DUE,
    )


def test_created_notification_names_the_follow_up_and_when() -> None:
    draft = draft_for_pending_item_event("c9.pending_item.created", {}, _item())
    assert draft is not None
    assert draft.kind == InAppNotificationKind.PENDING_ITEM_CREATED
    assert draft.title == "New follow-up: Waiting for a result: Ferritin"
    assert "4 Oct 2026" in draft.body
    assert draft.idempotency_key == f"c9:{_ITEM_ID}:created"


def test_due_notification_title_and_epoch_scoped_key() -> None:
    draft = draft_for_pending_item_event(
        "c9.pending_item.due", {"timer_epoch": 0}, _item(status="due")
    )
    assert draft is not None
    assert draft.title == "A follow-up is due: Waiting for a result: Ferritin"
    assert draft.idempotency_key == f"c9:{_ITEM_ID}:due:0"


def test_overdue_notification_is_calm() -> None:
    draft = draft_for_pending_item_event(
        "c9.pending_item.overdue", {"timer_epoch": 1}, _item(status="overdue")
    )
    assert draft is not None
    assert draft.kind == InAppNotificationKind.PENDING_ITEM_OVERDUE
    assert draft.title.startswith("Still open: ")
    assert draft.idempotency_key == f"c9:{_ITEM_ID}:overdue:1"


def test_same_event_twice_yields_the_same_key() -> None:
    a = draft_for_pending_item_event("c9.pending_item.due", {"timer_epoch": 3}, _item("due"))
    b = draft_for_pending_item_event("c9.pending_item.due", {"timer_epoch": 3}, _item("due"))
    assert a is not None and b is not None
    assert a.idempotency_key == b.idempotency_key


@pytest.mark.parametrize("status", ["resolved", "cancelled", "superseded"])
def test_settled_items_produce_no_notification(status: str) -> None:
    for event in ("c9.pending_item.created", "c9.pending_item.due", "c9.pending_item.overdue"):
        assert draft_for_pending_item_event(event, {"timer_epoch": 0}, _item(status)) is None


def test_due_is_superseded_once_the_item_is_overdue() -> None:
    assert (
        draft_for_pending_item_event("c9.pending_item.due", {"timer_epoch": 0}, _item("overdue"))
        is None
    )


def test_missing_item_or_unknown_event_is_skipped() -> None:
    assert draft_for_pending_item_event("c9.pending_item.due", {}, None) is None
    assert draft_for_pending_item_event("c9.pending_item.resolved", {}, _item()) is None


_ALARMING = re.compile(
    r"\b(urgent|warning|alert|danger|abnormal|diagnos\w*|immediately|emergency|overdue)\b",
    re.I,
)


@pytest.mark.parametrize("kind", list(InAppNotificationKind))
@pytest.mark.parametrize("item_type", ["result_pending", "referral_pending", "follow_up_due"])
def test_copy_is_non_alarming_and_non_diagnostic(
    kind: InAppNotificationKind, item_type: str
) -> None:
    title, body = render_pending_item_copy(
        kind, item_title="Waiting for a result: Ferritin", item_type=item_type, due_at=_DUE
    )
    assert not _ALARMING.search(title), title
    assert not _ALARMING.search(body), body


def test_long_titles_are_clipped() -> None:
    title, _ = render_pending_item_copy(
        InAppNotificationKind.PENDING_ITEM_DUE,
        item_title="x" * 500,
        item_type="result_pending",
        due_at=None,
    )
    assert len(title) <= 200 and title.endswith("…")
