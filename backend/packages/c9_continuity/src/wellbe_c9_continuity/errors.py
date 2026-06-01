from __future__ import annotations

import uuid


class ContinuityError(Exception):
    """Base class for C9 continuity errors."""


class PendingItemNotFoundError(ContinuityError):
    def __init__(self, pending_item_id: uuid.UUID) -> None:
        self.pending_item_id = pending_item_id
        super().__init__(f"Pending item {pending_item_id} not found")


class OutOfOrderThreadEventError(ContinuityError):
    """Raised when a thread.state_changed event arrives before its predecessor.

    The consumer should park the event and request replay rather than apply it.
    """

    def __init__(self, thread_id: uuid.UUID, expected_seq: int, got_seq: int) -> None:
        self.thread_id = thread_id
        self.expected_seq = expected_seq
        self.got_seq = got_seq
        super().__init__(
            f"Thread {thread_id} event out of order: expected seq {expected_seq}, got {got_seq}"
        )
