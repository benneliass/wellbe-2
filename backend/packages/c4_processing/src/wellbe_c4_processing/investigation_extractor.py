from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from wellbe_contracts.c4_processing import QualityFlag

from wellbe_c4_processing.extractor import compute_quality_flag


@dataclass(frozen=True)
class TheoryClaimResult:
    object_type: str
    claim_text: str
    normalized_key: str
    extraction_confidence: float
    quality_flag: QualityFlag
    diagnostic_assertion: bool = False
    quality_metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalClaimResult:
    source_id: str
    claim_text: str
    normalized_key: str
    source_scope: str
    source_quality_tier: int
    personal_evidence: bool
    extraction_confidence: float
    quality_flag: QualityFlag


class TheoryClaimExtractor:
    """Extracts hypothesis/theory text without converting it into patient facts."""

    async def extract(self, text: str) -> list[TheoryClaimResult]:
        normalized = text.strip()
        if not normalized:
            return []
        confidence = 0.72 if _looks_theory_like(normalized) else 0.55
        return [
            TheoryClaimResult(
                object_type="theory",
                claim_text=normalized,
                normalized_key=_make_hash(normalized),
                extraction_confidence=confidence,
                quality_flag=compute_quality_flag(confidence),
                diagnostic_assertion=False,
                quality_metadata={"method": "theory_claim_keyword_scope"},
            )
        ]


class ExternalClaimExtractor:
    """Extracts claims from external sources while preserving external scope."""

    async def extract(
        self,
        *,
        source_id: str,
        source_quality_tier: int,
        text: str,
    ) -> ExternalClaimResult:
        confidence = 0.80 if source_quality_tier <= 2 else 0.62
        return ExternalClaimResult(
            source_id=source_id,
            claim_text=text.strip(),
            normalized_key=_make_hash(f"{source_id}:{text.strip()}"),
            source_scope="external",
            source_quality_tier=source_quality_tier,
            personal_evidence=False,
            extraction_confidence=confidence,
            quality_flag=compute_quality_flag(confidence),
        )


def _looks_theory_like(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in ("possible", "may explain", "could explain"))


def _make_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
