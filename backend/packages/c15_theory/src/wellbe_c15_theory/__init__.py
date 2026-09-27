"""C15 Theory Service.

Public surface for the Theory aggregate, its evaluator, and the deterministic
non-diagnosis normalizer. All user-facing theory output is routed through C10.
"""

from __future__ import annotations

from wellbe_c15_theory.errors import (
    TheoryBlockedError,
    TheoryError,
    TheoryEvaluationError,
    TheoryEvidenceNotFoundError,
    TheoryEvidenceRequiredError,
    TheoryEvidenceUnrelatedError,
    TheoryNotFoundError,
    TheoryNotLinkedError,
    TheoryRationaleRequiredError,
    TheoryVersionConflictError,
)
from wellbe_c15_theory.normalizer import normalize_theory_text
from wellbe_c15_theory.repository import TheoryRepository
from wellbe_c15_theory.service import (
    TheoryService,
    UserEvaluationOutcome,
    user_evaluation_from_row,
)
from wellbe_c15_theory.status_rules import status_from_personal_evidence

__all__ = [
    "TheoryService",
    "TheoryRepository",
    "normalize_theory_text",
    "status_from_personal_evidence",
    "TheoryError",
    "TheoryNotFoundError",
    "TheoryBlockedError",
    "TheoryEvaluationError",
    "TheoryEvidenceNotFoundError",
    "TheoryEvidenceRequiredError",
    "TheoryEvidenceUnrelatedError",
    "TheoryNotLinkedError",
    "TheoryRationaleRequiredError",
    "TheoryVersionConflictError",
    "UserEvaluationOutcome",
    "user_evaluation_from_row",
]
