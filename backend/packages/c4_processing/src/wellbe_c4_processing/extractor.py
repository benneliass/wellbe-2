from __future__ import annotations

import hashlib
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from wellbe_contracts.c4_processing import (
    FactType,
    QualityFlag,
    SubjectType,
)

from wellbe_c4_processing.vital_registry import VITAL_REGISTRY_VERSION, classify_vital

PIPELINE_VERSION = "0.1.0"

# Governs the structured-observation typing contract (capture_type=lab → fact_type).
# Bump the major on any change that would reclassify an existing normalized key
# (which requires a backfill); additive changes keep the major stable.
STRUCTURED_CONTRACT_VERSION = "structured-capture-contract-v1"


@dataclass(frozen=True)
class ExtractionResult:
    fact_type: FactType
    entity_label: str
    normalized_key: str
    extraction_confidence: float
    quality_flag: QualityFlag
    quality_metadata: dict[str, Any] = field(default_factory=dict)
    code_system: str | None = None
    code: str | None = None
    text_span_start: int | None = None
    text_span_end: int | None = None
    is_negated: bool = False
    is_historical: bool = False
    is_hypothetical: bool = False
    subject: SubjectType = SubjectType.PATIENT


def compute_quality_flag(confidence: float, is_partial: bool = False) -> QualityFlag:
    if is_partial:
        return QualityFlag.PARTIAL
    if confidence >= 0.85:
        return QualityFlag.CLEAN
    if confidence >= 0.60:
        return QualityFlag.LOW_CONFIDENCE
    return QualityFlag.REQUIRES_REVIEW


class FactExtractor(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def model_version(self) -> str: ...

    @abstractmethod
    async def extract(self, text: str, patient_id: uuid.UUID) -> list[ExtractionResult]: ...


class TextFactExtractor(FactExtractor):
    """Rule-based / lightweight extraction for MVP.

    This is a placeholder implementation that uses keyword matching.
    In production this would delegate to an LLM or NER model.
    """

    @property
    def model_name(self) -> str:
        return "wellbe-text-extractor"

    @property
    def model_version(self) -> str:
        return "0.1.0"

    async def extract(self, text: str, patient_id: uuid.UUID) -> list[ExtractionResult]:
        results: list[ExtractionResult] = []
        lower = text.lower()

        symptom_keywords = {
            "headache": "headache",
            "nausea": "nausea",
            "fatigue": "fatigue",
            "dizziness": "dizziness",
            "pain": "pain",
            "fever": "fever",
            "cough": "cough",
            "chest pain": "chest_pain",
            "shortness of breath": "shortness_of_breath",
            "insomnia": "insomnia",
        }

        for keyword, normalized in symptom_keywords.items():
            start = lower.find(keyword)
            if start == -1:
                continue
            confidence = 0.90
            results.append(ExtractionResult(
                fact_type=FactType.SYMPTOM,
                entity_label=keyword,
                normalized_key=normalized,
                extraction_confidence=confidence,
                quality_flag=compute_quality_flag(confidence),
                quality_metadata={"method": "keyword_match"},
                text_span_start=start,
                text_span_end=start + len(keyword),
                is_negated=_check_negation(lower, start),
            ))

        medication_keywords = {
            "ibuprofen": "ibuprofen",
            "paracetamol": "paracetamol",
            "aspirin": "aspirin",
            "metformin": "metformin",
        }

        for keyword, normalized in medication_keywords.items():
            start = lower.find(keyword)
            if start == -1:
                continue
            confidence = 0.92
            results.append(ExtractionResult(
                fact_type=FactType.MEDICATION,
                entity_label=keyword,
                normalized_key=normalized,
                extraction_confidence=confidence,
                quality_flag=compute_quality_flag(confidence),
                quality_metadata={"method": "keyword_match"},
                text_span_start=start,
                text_span_end=start + len(keyword),
            ))

        if not results:
            confidence = 0.50
            results.append(ExtractionResult(
                fact_type=FactType.OTHER,
                entity_label=text[:50].strip(),
                normalized_key=_make_hash(text),
                extraction_confidence=confidence,
                quality_flag=compute_quality_flag(confidence),
                quality_metadata={"method": "fallback", "reason": "no_keywords_matched"},
            ))

        return results


def _slug(text: str) -> str:
    """Stable lowercase slug for an observation concept (e.g. "ldl_cholesterol")."""
    return re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower()).strip("_")


def _parse_blood_pressure(value: str) -> dict[str, float] | None:
    """Best-effort parse of a "systolic/diastolic" reading into components.

    Returns ``None`` when the value is not in the expected shape — the fact is
    still typed ``vital_sign``; we simply omit parsed components (raw_only).
    """
    match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", value or "")
    if not match:
        return None
    return {"systolic": float(match.group(1)), "diastolic": float(match.group(2))}


class StructuredObservationExtractor:
    """Deterministic typing for structured ``capture_type=lab`` payloads (WEL-185).

    Per docs/decisions/structured-capture-extraction-typing.md (Approach 1):
    a lab payload becomes a ``vital_sign`` fact when its test name matches the
    governed ``VitalConceptRegistry``, otherwise a ``lab_result`` fact. Typing is
    never blocked on terminology — we emit the raw test_name/value/unit/reference
    plus a normalized key, nullable code fields, and a ``normalization_status``.
    No clinical interpretation (normality/abnormality) is ever computed; a
    source-provided abnormal flag is stored only as source metadata.

    This class is intentionally not a ``FactExtractor`` subclass: it consumes
    structured fields, not free text. It exposes ``model_name``/``model_version``
    so the worker can treat it uniformly with ``TextFactExtractor``.
    """

    model_name = "wellbe-structured-observation-extractor"
    model_version = "0.1.0"

    def extract_lab(
        self,
        *,
        test_name: str,
        value: str,
        unit: str | None = None,
        reference_range: str | None = None,
        occurrence: date | datetime | None = None,
        abnormal_flag: str | None = None,
    ) -> list[ExtractionResult]:
        """Type a structured lab capture into exactly one ExtractedFact.

        ``occurrence`` (capture/effective time) is folded into the normalized key
        so distinct readings over time stay distinct graph nodes while the same
        raw event stays idempotent (decision §5). Same-day re-entry of the same
        concept merges.
        """
        test_name = (test_name or "").strip()
        value = "" if value is None else str(value).strip()

        # No observation identity → safe Other, flagged for review (decision Q5 /
        # findings "malformed captures"). Never guess a type from nothing.
        if not test_name or not value:
            label = (test_name or value or "lab observation")[:50].strip()
            return [
                ExtractionResult(
                    fact_type=FactType.OTHER,
                    entity_label=label or "lab observation",
                    normalized_key=f"lab:unidentified:{_make_hash(f'{test_name}|{value}')}",
                    extraction_confidence=0.50,
                    quality_flag=QualityFlag.REQUIRES_REVIEW,
                    quality_metadata={
                        "method": "structured_capture",
                        "contract_version": STRUCTURED_CONTRACT_VERSION,
                        "reason": "missing_observation_identity",
                    },
                )
            ]

        vital = classify_vital(test_name)
        if vital is not None:
            fact_type = FactType.VITAL_SIGN
            concept = vital.key
            kind = "vital"
        else:
            fact_type = FactType.LAB_RESULT
            concept = _slug(test_name)
            kind = "lab"

        occurrence_token = _occurrence_token(occurrence)
        normalized_key = f"{kind}:{concept}:{occurrence_token}"

        quality_metadata: dict[str, Any] = {
            "method": "structured_capture",
            "contract_version": STRUCTURED_CONTRACT_VERSION,
            "normalization_status": "raw_only",
            "raw_test_name": test_name,
            "raw_value": value,
            "raw_unit": unit or None,
            "reference_range": reference_range or None,
        }
        if vital is not None:
            quality_metadata["vital_registry_version"] = VITAL_REGISTRY_VERSION
            quality_metadata["vital_concept"] = concept
            if vital.composite:
                components = _parse_blood_pressure(value)
                if components is not None:
                    quality_metadata["components"] = components
        # Source-provided flag is stored as provenance only — never a WellBe judgment.
        if abnormal_flag:
            quality_metadata["source_provided_flag"] = str(abnormal_flag)

        return [
            ExtractionResult(
                fact_type=fact_type,
                entity_label=test_name,
                normalized_key=normalized_key,
                # Structured capture is deterministic and high-precision.
                extraction_confidence=0.97,
                quality_flag=QualityFlag.CLEAN,
                quality_metadata=quality_metadata,
                code_system=None,
                code=None,
            )
        ]


def _occurrence_token(occurrence: date | datetime | None) -> str:
    """Calendar-day token for the normalized key (occurrence/effective time).

    Day granularity keeps same-day re-entries idempotent while distinguishing
    readings on different days. ``unknown`` when no occurrence time is available
    (deterministic fact id still disambiguates by raw event).
    """
    if occurrence is None:
        return "unknown"
    if isinstance(occurrence, datetime):
        return occurrence.date().isoformat()
    return occurrence.isoformat()


def _check_negation(text: str, span_start: int) -> bool:
    prefix = text[max(0, span_start - 15):span_start]
    negation_cues = ("no ", "not ", "don't ", "doesn't ", "without ", "deny ", "denies ")
    return any(cue in prefix for cue in negation_cues)


def _make_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
