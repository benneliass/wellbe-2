from __future__ import annotations

import uuid

from wellbe_c14_investigation.coupling import evaluate_close
from wellbe_contracts.c7_thread import HealthThreadStatus, ThreadClosureSnapshot


def _snap(status: HealthThreadStatus, resolved: bool) -> ThreadClosureSnapshot:
    return ThreadClosureSnapshot(
        thread_id=uuid.uuid4(), status=status, status_version=2, is_resolved=resolved
    )


def test_close_allowed_when_no_threads():
    assert evaluate_close([]).allowed is True


def test_close_allowed_when_all_resolved():
    snaps = [
        _snap(HealthThreadStatus.EXPLAINED, True),
        _snap(HealthThreadStatus.CLOSED, True),
    ]
    result = evaluate_close(snaps)
    assert result.allowed is True
    assert result.unmet_thread_ids == []


def test_close_denied_when_any_unresolved():
    unresolved = _snap(HealthThreadStatus.ACTIVE_UNRESOLVED, False)
    snaps = [_snap(HealthThreadStatus.EXPLAINED, True), unresolved]
    result = evaluate_close(snaps)
    assert result.allowed is False
    assert unresolved.thread_id in result.unmet_thread_ids
    assert result.reason == "linked_threads_unresolved"
