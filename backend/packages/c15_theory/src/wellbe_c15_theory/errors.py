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


class TheoryEvaluationError(TheoryError):
    """A user evaluation was rejected; ``code`` is a stable, client-facing reason."""

    code = "theory_evaluation_invalid"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class TheoryEvidenceRequiredError(TheoryEvaluationError):
    code = "theory_evidence_required"


class TheoryRationaleRequiredError(TheoryEvaluationError):
    code = "theory_rationale_required"


class TheoryNotLinkedError(TheoryEvaluationError):
    code = "theory_not_linked_to_investigation"


class TheoryEvidenceNotFoundError(TheoryEvaluationError):
    """The ref does not exist or does not belong to this patient (not disclosed which)."""

    code = "theory_evidence_not_found"

    def __init__(self, kind: str, ref_id: object) -> None:
        self.kind = kind
        self.ref_id = ref_id
        super().__init__(f"No {kind} {ref_id} is visible for this patient.")


class TheoryEvidenceUnrelatedError(TheoryEvaluationError):
    """The ref belongs to the patient but not to any thread linked to the investigation."""

    code = "theory_evidence_unrelated"

    def __init__(self, kind: str, ref_id: object) -> None:
        self.kind = kind
        self.ref_id = ref_id
        super().__init__(
            f"The {kind} {ref_id} is not part of any thread linked to this investigation."
        )


class TheoryVersionConflictError(TheoryError):
    def __init__(self, theory_id: object, expected: int, actual: int) -> None:
        self.theory_id = theory_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Theory {theory_id} is at version {actual}, not the expected {expected}"
        )
