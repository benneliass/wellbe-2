from __future__ import annotations

import uuid


class CorrectionError(Exception):
    """Base class for C11 correction errors."""


class CorrectionNotFoundError(CorrectionError):
    def __init__(self, correction_id: uuid.UUID) -> None:
        self.correction_id = correction_id
        super().__init__(f"Correction {correction_id} not found")


class CorrectionNotPendingError(CorrectionError):
    """Raised when accepting a correction that is not pending controller acceptance."""

    def __init__(self, correction_id: uuid.UUID, status: str) -> None:
        self.correction_id = correction_id
        self.status = status
        super().__init__(
            f"Correction {correction_id} is '{status}', not pending acceptance"
        )


class TargetMutationError(CorrectionError):
    """Raised if a code path attempts to mutate a correction target (forbidden)."""
