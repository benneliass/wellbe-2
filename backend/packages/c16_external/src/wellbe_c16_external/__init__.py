"""C16 External Evidence Graph + Research Relevance engine.

External medical knowledge is context, never fact about the user. The only
personal<->external connection is the context-only relevance-link bridge.
"""

from __future__ import annotations

from wellbe_c16_external.errors import (
    ExternalEvidenceError,
    ExternalSourceNotFoundError,
    PersonalNodeNotFoundError,
    TierUpgradeByUsageError,
)
from wellbe_c16_external.models import ExternalClaimRow, SourceQualityReviewRow
from wellbe_c16_external.repository import ExternalEvidenceRepository
from wellbe_c16_external.scoring import compute_relevance_score
from wellbe_c16_external.service import ExternalEvidenceService

__all__ = [
    "ExternalEvidenceService",
    "ExternalEvidenceRepository",
    "compute_relevance_score",
    "ExternalClaimRow",
    "SourceQualityReviewRow",
    "ExternalEvidenceError",
    "ExternalSourceNotFoundError",
    "PersonalNodeNotFoundError",
    "TierUpgradeByUsageError",
]
