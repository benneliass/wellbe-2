from __future__ import annotations

from enum import Enum
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from wellbe_contracts.primitives import AwareDatetime, EventId, PatientId

# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

FACT_EXTRACTED = "fact.extracted"
HEALTH_SIGNAL_CREATED = "health_signal.created"
DOCUMENT_OCR_COMPLETED = "document.ocr_completed"
DOCUMENT_OCR_FAILED = "document.ocr_failed"

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

FactId = Annotated[UUID, Field(description="Unique identifier for an ExtractedFact")]
SignalId = Annotated[UUID, Field(description="Unique identifier for a HealthSignal")]


class FactType(str, Enum):
    SYMPTOM = "symptom"
    FINDING = "finding"
    MEDICATION = "medication"
    LAB_RESULT = "lab_result"
    ALLERGY = "allergy"
    PROCEDURE = "procedure"
    DX_MENTION = "dx_mention"
    VITAL_SIGN = "vital_sign"
    IMMUNIZATION = "immunization"
    FAMILY_HISTORY = "family_history"
    SOCIAL_HISTORY = "social_history"
    OTHER = "other"


class QualityFlag(str, Enum):
    CLEAN = "clean"
    LOW_CONFIDENCE = "low_confidence"
    REQUIRES_REVIEW = "requires_review"
    PARTIAL = "partial"


class SubjectType(str, Enum):
    PATIENT = "patient"
    FAMILY_MEMBER = "family_member"
    OTHER = "other"


class SignalType(str, Enum):
    PAIN_LEVEL = "pain_level"
    MOOD_SCORE = "mood_score"
    FATIGUE = "fatigue"
    SLEEP_QUALITY = "sleep_quality"
    SLEEP_DURATION = "sleep_duration"
    ENERGY_LEVEL = "energy_level"
    ANXIETY_LEVEL = "anxiety_level"
    APPETITE = "appetite"
    HEART_RATE = "heart_rate"
    BLOOD_PRESSURE = "blood_pressure"
    BLOOD_GLUCOSE = "blood_glucose"
    WEIGHT = "weight"
    STEPS = "steps"
    OTHER = "other"


class SignalDirection(str, Enum):
    IMPROVING = "improving"
    WORSENING = "worsening"
    STABLE = "stable"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Core output types
# ---------------------------------------------------------------------------


class ExtractedFact(BaseModel):
    """A discrete factual claim extracted from a RawContextEvent.

    Every instance must have a non-null raw_context_event_id linking it back
    to the immutable source in C2. C5 enforces this via the no-orphan-claims
    rule at write time.
    """

    model_config = ConfigDict(from_attributes=True)

    id: FactId
    patient_id: PatientId
    raw_context_event_id: EventId

    fact_type: FactType
    entity_label: str
    normalized_key: str
    code_system: Optional[str] = None
    code: Optional[str] = None

    text_span_start: Optional[int] = None
    text_span_end: Optional[int] = None
    source_text_excerpt_hash: Optional[str] = None

    extraction_confidence: float = Field(ge=0.0, le=1.0)
    extraction_model: str
    model_version: str
    pipeline_version: str

    quality_flag: QualityFlag
    quality_metadata: Optional[dict] = None

    is_negated: bool = False
    is_historical: bool = False
    is_hypothetical: bool = False
    subject: SubjectType = SubjectType.PATIENT

    captured_at: AwareDatetime
    extracted_at: AwareDatetime
    correlation_id: str
    trace_id: str
    schema_version: int = 1
    created_at: AwareDatetime


class HealthSignal(BaseModel):
    """An aggregate or computed signal derived from one or more RawContextEvents.

    raw_context_event_ids is an array — a signal may aggregate multiple raw
    events (e.g. pain levels logged across a day). C5 creates one EvidenceLink
    per event ID in this array.
    """

    model_config = ConfigDict(from_attributes=True)

    id: SignalId
    patient_id: PatientId
    raw_context_event_ids: list[EventId]

    signal_type: SignalType
    signal_value: float
    signal_unit: Optional[str] = None
    signal_direction: Optional[SignalDirection] = None

    aggregation_method: Optional[str] = None
    observation_window: Optional[str] = None

    extraction_confidence: float = Field(ge=0.0, le=1.0)
    extraction_model: str
    model_version: str
    pipeline_version: str

    quality_flag: QualityFlag
    quality_metadata: Optional[dict] = None

    captured_at_start: AwareDatetime
    captured_at_end: AwareDatetime
    extracted_at: AwareDatetime
    correlation_id: str
    trace_id: str
    schema_version: int = 1
    created_at: AwareDatetime


# ---------------------------------------------------------------------------
# Event payloads emitted on the outbox
# ---------------------------------------------------------------------------


class FactExtractedPayload(BaseModel):
    """Payload for the fact.extracted outbox event consumed by C5 and C6."""

    fact_id: FactId
    patient_id: PatientId
    raw_context_event_id: EventId
    fact_type: FactType
    entity_label: str
    normalized_key: str
    extraction_confidence: float
    quality_flag: QualityFlag
    correlation_id: str
    trace_id: str


class HealthSignalCreatedPayload(BaseModel):
    """Payload for the health_signal.created outbox event consumed by C5 and C6."""

    signal_id: SignalId
    patient_id: PatientId
    raw_context_event_ids: list[EventId]
    signal_type: SignalType
    signal_value: float
    extraction_confidence: float
    quality_flag: QualityFlag
    correlation_id: str
    trace_id: str


class DocumentOCRCompletedPayload(BaseModel):
    """Payload for document.ocr_completed — signals that OCR succeeded and
    ExtractedFacts were created from the OCR output."""

    raw_context_event_id: EventId
    patient_id: PatientId
    fact_ids: list[FactId]
    ocr_model: str
    ocr_confidence: float
    correlation_id: str
    trace_id: str


class DocumentOCRFailedPayload(BaseModel):
    """Payload for document.ocr_failed — OCR exhausted all fallback paths.
    quality_flag is always requires_review."""

    raw_context_event_id: EventId
    patient_id: PatientId
    failure_reason: str
    quality_flag: QualityFlag = QualityFlag.REQUIRES_REVIEW
    correlation_id: str
    trace_id: str


__all__ = [
    # Event type constants
    "FACT_EXTRACTED",
    "HEALTH_SIGNAL_CREATED",
    "DOCUMENT_OCR_COMPLETED",
    "DOCUMENT_OCR_FAILED",
    # Type aliases
    "FactId",
    "SignalId",
    # Enums
    "FactType",
    "HealthSignalCreatedPayload",
    "QualityFlag",
    "SignalDirection",
    "SignalType",
    "SubjectType",
    # Core output models
    "ExtractedFact",
    "HealthSignal",
    # Event payloads
    "DocumentOCRCompletedPayload",
    "DocumentOCRFailedPayload",
    "FactExtractedPayload",
]
