from __future__ import annotations

from wellbe_contracts.c14_investigation import CloseEvaluation, InvestigationStatus


class InvestigationError(Exception):
    """Base class for C14 errors."""


class InvestigationNotFoundError(InvestigationError):
    def __init__(self, investigation_id: object) -> None:
        self.investigation_id = investigation_id
        super().__init__(f"Investigation not found: {investigation_id}")


class InvalidInvestigationTransitionError(InvestigationError):
    def __init__(
        self, from_status: InvestigationStatus, to_status: InvestigationStatus
    ) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Illegal investigation transition: {from_status.value} -> {to_status.value}"
        )


class ClosureBlockedByThreadError(InvestigationError):
    """Raised when closure is denied because a linked thread is unresolved (G4)."""

    def __init__(self, evaluation: CloseEvaluation) -> None:
        self.evaluation = evaluation
        super().__init__(
            "Investigation cannot close while linked threads are unresolved: "
            + ", ".join(str(t) for t in evaluation.unmet_thread_ids)
        )


class InvestigationVersionConflictError(InvestigationError):
    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Version conflict: expected status_version {expected}, found {actual}"
        )
