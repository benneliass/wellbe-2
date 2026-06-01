from __future__ import annotations

import uuid

from wellbe_contracts.c9_continuity import (
    TERMINAL_STATUSES,
    PendingItemStatus,
    workflow_id,
)


def test_workflow_id_is_deterministic() -> None:
    pid = uuid.uuid4()
    assert workflow_id(pid) == f"c9-pending-{pid}"
    assert workflow_id(pid) == workflow_id(pid)


def test_terminal_statuses() -> None:
    assert PendingItemStatus.RESOLVED in TERMINAL_STATUSES
    assert PendingItemStatus.CANCELLED in TERMINAL_STATUSES
    assert PendingItemStatus.SUPERSEDED in TERMINAL_STATUSES
    assert PendingItemStatus.ACTIVE not in TERMINAL_STATUSES
    assert PendingItemStatus.DUE not in TERMINAL_STATUSES
