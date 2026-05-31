from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from wellbe_contracts.c4_processing import (
    FactType,
    QualityFlag,
    SubjectType,
)

PIPELINE_VERSION = "0.1.0"


@dataclass(frozen=True)
class ExtractionResult:
    fact_type: FactType
    entity_label: str
    normalized_key: str
    extraction_confidence: float
    quality_flag: QualityFlag
    quality_metadata: dict = field(default_factory=dict)
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


def _check_negation(text: str, span_start: int) -> bool:
    prefix = text[max(0, span_start - 15):span_start]
    negation_cues = ("no ", "not ", "don't ", "doesn't ", "without ", "deny ", "denies ")
    return any(cue in prefix for cue in negation_cues)


def _make_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
