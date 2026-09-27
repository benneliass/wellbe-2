from __future__ import annotations

import hashlib
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, TypedDict

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
        taken: list[tuple[int, int]] = []

        for fact_type, pattern, normalized, label, confidence in _LEXICON:
            for match in pattern.finditer(lower):
                start, end = match.span()
                if any(s < end and start < e for s, e in taken):
                    continue
                taken.append((start, end))
                key, shown = normalized, label
                site = match.groupdict().get("site")
                if site:
                    key = f"{normalized}:{_slug(site)}"
                    shown = f"{site} {label}"
                results.append(ExtractionResult(
                    fact_type=fact_type,
                    entity_label=shown,
                    normalized_key=key,
                    extraction_confidence=confidence,
                    quality_flag=compute_quality_flag(confidence),
                    quality_metadata={
                        "method": "lexicon_match",
                        "lexicon_version": LEXICON_VERSION,
                        "surface": text[start:end],
                    },
                    text_span_start=start,
                    text_span_end=end,
                    is_negated=(
                        _check_negation(lower, start)
                        if fact_type is FactType.SYMPTOM
                        else False
                    ),
                ))
                break  # first mention per concept; repeats add no new fact

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
    prefix = text[max(0, span_start - 25):span_start]
    # A cue never negates across a sentence/clause boundary ("No fever. Cough.").
    prefix = re.split(r"[.;!?\n]|\bbut\b", prefix)[-1]
    negation_cues = (
        "no ", "not ", "don't ", "doesn't ", "without ", "deny ", "denies ", "never ",
        "free of ", "resolved ",
    )
    return any(cue in f" {prefix}" for cue in negation_cues)


# Rule-based lexicon (placeholder for an NER/LLM extractor). Each concept is one
# alternation of surface forms, matched on word boundaries, longest form first,
# so "chest pain" never also yields a generic "pain" and "tired" maps to fatigue.
LEXICON_VERSION = "text-lexicon-v2"

_BODY_SITES = (
    "knee", "back", "lower back", "neck", "shoulder", "hip", "ankle", "wrist", "elbow",
    "foot", "hand", "joint", "stomach", "abdominal", "belly", "ear", "eye", "tooth",
    "jaw", "leg", "arm", "muscle",
)

_CONCEPTS: list[tuple[FactType, str, str, tuple[str, ...], float]] = [
    (FactType.SYMPTOM, "chest_pain", "chest pain", ("chest pain", "chest tightness"), 0.90),
    (FactType.SYMPTOM, "shortness_of_breath", "shortness of breath",
     ("shortness of breath", "short of breath", "breathless", "breathlessness"), 0.90),
    (FactType.SYMPTOM, "headache", "headache",
     ("headaches", "headache", "migraines", "migraine", "head ache", "head hurts"), 0.90),
    (FactType.SYMPTOM, "fatigue", "fatigue",
     ("fatigue", "fatigued", "tiredness", "tired", "exhausted", "exhaustion", "low energy",
      "no energy", "worn out", "lethargic", "lethargy"), 0.88),
    (FactType.SYMPTOM, "dizziness", "dizziness",
     ("dizziness", "dizzy", "lightheaded", "light-headed", "light headed", "vertigo"), 0.90),
    (FactType.SYMPTOM, "nausea", "nausea", ("nausea", "nauseous", "nauseated", "queasy"), 0.90),
    (FactType.SYMPTOM, "vomiting", "vomiting", ("vomiting", "vomited", "throwing up"), 0.90),
    (FactType.SYMPTOM, "fever", "fever", ("fever", "feverish", "high temperature"), 0.90),
    (FactType.SYMPTOM, "cough", "cough", ("coughing", "cough"), 0.90),
    (FactType.SYMPTOM, "sore_throat", "sore throat", ("sore throat",), 0.90),
    (FactType.SYMPTOM, "insomnia", "insomnia",
     ("insomnia", "can't sleep", "cannot sleep", "trouble sleeping", "poor sleep"), 0.88),
    (FactType.SYMPTOM, "palpitations", "palpitations",
     ("palpitations", "heart racing", "racing heart", "heart pounding"), 0.90),
    (FactType.SYMPTOM, "rash", "rash", ("rash", "hives"), 0.88),
    (FactType.SYMPTOM, "diarrhea", "diarrhea", ("diarrhea", "diarrhoea"), 0.90),
    (FactType.SYMPTOM, "constipation", "constipation", ("constipation", "constipated"), 0.90),
    (FactType.SYMPTOM, "anxiety", "anxiety", ("anxiety", "anxious", "panic attack"), 0.85),
    (FactType.SYMPTOM, "low_mood", "low mood", ("low mood", "depressed", "feeling down"), 0.85),
    (FactType.SYMPTOM, "numbness", "numbness", ("numbness", "numb", "tingling", "pins and needles"),
     0.88),
    (FactType.MEDICATION, "iron_supplement", "iron supplement",
     ("iron supplements", "iron supplement", "iron tablets", "iron pills", "ferrous sulfate",
      "ferrous sulphate", "ferrous fumarate"), 0.90),
    (FactType.MEDICATION, "vitamin_d_supplement", "vitamin D supplement",
     ("vitamin d supplement", "vitamin d3", "cholecalciferol"), 0.90),
    (FactType.MEDICATION, "vitamin_b12_supplement", "vitamin B12 supplement",
     ("b12 supplement", "b12 injection", "cyanocobalamin"), 0.90),
    (FactType.MEDICATION, "ibuprofen", "ibuprofen", ("ibuprofen", "advil", "nurofen"), 0.92),
    (FactType.MEDICATION, "paracetamol", "paracetamol",
     ("paracetamol", "acetaminophen", "tylenol"), 0.92),
    (FactType.MEDICATION, "aspirin", "aspirin", ("aspirin",), 0.92),
    (FactType.MEDICATION, "metformin", "metformin", ("metformin",), 0.92),
    (FactType.MEDICATION, "levothyroxine", "levothyroxine", ("levothyroxine", "synthroid"), 0.92),
    (FactType.MEDICATION, "omeprazole", "omeprazole", ("omeprazole",), 0.92),
]


def _alternation(forms: tuple[str, ...]) -> str:
    return "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True))


def _compile_lexicon() -> list[tuple[FactType, re.Pattern[str], str, str, float]]:
    sites = _alternation(_BODY_SITES)
    lexicon: list[tuple[FactType, re.Pattern[str], str, str, float]] = [
        (
            FactType.SYMPTOM,
            re.compile(rf"\b(?P<site>{sites})\s+(?:pain|ache|aches|hurts|soreness)\b"),
            "pain",
            "pain",
            0.88,
        ),
    ]
    for fact_type, normalized, label, forms, confidence in _CONCEPTS:
        lexicon.append((
            fact_type,
            re.compile(rf"\b(?:{_alternation(forms)})\b"),
            normalized,
            label,
            confidence,
        ))
    # Generic pain only when no more specific form claimed the span.
    lexicon.append((
        FactType.SYMPTOM, re.compile(r"\b(?:pain|painful|aches?)\b"), "pain", "pain", 0.80,
    ))
    return lexicon


_LEXICON = _compile_lexicon()

_LAB_LINE = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z0-9 ,\-()]{1,40}?)\s*[:=]\s*"
    r"(?P<value>[<>]?\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-zµ%/0-9\^.]+(?:/[A-Za-z]+)?)?"
    r"\s*(?:\((?:ref(?:erence)?(?: range)?|normal)?[:\s]*(?P<ref>[^)]*)\))?"
)


class LabLine(TypedDict):
    test_name: str
    value: str
    unit: str | None
    reference_range: str | None


def parse_lab_lines(text: str) -> list[LabLine]:
    """Find ``Name: value unit (ref low-high)`` observations in document text.

    Requires a unit or a reference range so prose like "Pain: 7" is not mistaken
    for a lab. Returns kwargs for ``StructuredObservationExtractor.extract_lab``.
    """
    found: list[LabLine] = []
    seen: set[str] = set()
    for line in re.split(r"[\n;]", text or ""):
        for m in _LAB_LINE.finditer(line):
            unit, ref = m.group("unit"), m.group("ref")
            if not unit and not ref:
                continue
            name = m.group("name").strip(" ,-")
            if _slug(name) in seen:
                continue
            seen.add(_slug(name))
            found.append({
                "test_name": name,
                "value": m.group("value"),
                "unit": unit,
                "reference_range": (ref or "").strip() or None,
            })
    return found


def _make_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
