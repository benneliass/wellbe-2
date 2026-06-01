from __future__ import annotations


class TheoryError(Exception):
    """Base class for C15 errors."""


class TheoryNotFoundError(TheoryError):
    def __init__(self, theory_id: object) -> None:
        self.theory_id = theory_id
        super().__init__(f"Theory not found: {theory_id}")


class TheoryBlockedError(TheoryError):
    """Raised when an operation requires a non-blocked theory."""

    def __init__(self, theory_id: object) -> None:
        self.theory_id = theory_id
        super().__init__(
            f"Theory {theory_id} is blocked due to a diagnostic claim and cannot be evaluated"
        )
