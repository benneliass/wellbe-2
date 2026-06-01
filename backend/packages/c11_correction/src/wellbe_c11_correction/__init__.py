"""C11 Correction Service.

Append-only, source-linked correction overlays written through C5. Provides the
single shared deterministic resolver used by C6, C8, and C13 so corrected views
never diverge.
"""

from wellbe_c11_correction.errors import (
    CorrectionError,
    CorrectionNotFoundError,
    CorrectionNotPendingError,
    TargetMutationError,
)
from wellbe_c11_correction.resolver import (
    CandidateCorrection,
    resolve_overlays,
)
from wellbe_c11_correction.service import CorrectionService

__all__ = [
    "CorrectionService",
    "CandidateCorrection",
    "resolve_overlays",
    "CorrectionError",
    "CorrectionNotFoundError",
    "CorrectionNotPendingError",
    "TargetMutationError",
]
