from __future__ import annotations

from wellbe_contracts.c7_thread import HealthThreadStatus


class ThreadError(Exception):
    """Base class for C7 Health Thread errors."""


class ThreadNotFoundError(ThreadError):
    def __init__(self, thread_id: object) -> None:
        self.thread_id = thread_id
        super().__init__(f"Health thread not found: {thread_id}")


class InvalidTransitionError(ThreadError):
    """Raised when a transition is not a structurally allowed edge."""

    def __init__(
        self, from_status: HealthThreadStatus, to_status: HealthThreadStatus
    ) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Illegal transition: {from_status.value} -> {to_status.value}")


class ClosureSafetyError(ThreadError):
    """Raised when a transition violates a closure-safety guard.

    Encodes the non-negotiable safety rules from the decision record:
    a thread cannot be closed on a single normal test, cannot be closed while
    symptoms persist, and no transition may assert a final AI diagnosis.
    """

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__("Closure-safety guard rejected transition: " + ", ".join(violations))


class VersionConflictError(ThreadError):
    """Raised on optimistic-concurrency conflict (stale expected_version)."""

    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Version conflict: expected status_version {expected}, found {actual}"
        )
