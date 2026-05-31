from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DispatchRoute(StrEnum):
    DRAMATIQ_TEXT = "dramatiq_text"
    TEMPORAL_OCR = "temporal_ocr"
    TEMPORAL_FHIR = "temporal_fhir"
    TEMPORAL_DOCUMENT = "temporal_document"


_OCR_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/tiff", "application/pdf"})
_FHIR_SOURCE_TYPES = frozenset({"fhir"})
_STRUCTURED_SOURCE_TYPES = frozenset({"manual_text", "sms", "device"})


@dataclass(frozen=True)
class DispatchDecision:
    route: DispatchRoute
    source_type: str
    mime_type: str


def decide_route(source_type: str, mime_type: str) -> DispatchDecision:
    """Decide whether to route to Dramatiq (lightweight) or Temporal (durable)."""
    if source_type in _FHIR_SOURCE_TYPES:
        return DispatchDecision(
            route=DispatchRoute.TEMPORAL_FHIR,
            source_type=source_type,
            mime_type=mime_type,
        )

    if mime_type in _OCR_MIME_TYPES:
        return DispatchDecision(
            route=DispatchRoute.TEMPORAL_OCR,
            source_type=source_type,
            mime_type=mime_type,
        )

    if source_type in _STRUCTURED_SOURCE_TYPES:
        return DispatchDecision(
            route=DispatchRoute.DRAMATIQ_TEXT,
            source_type=source_type,
            mime_type=mime_type,
        )

    return DispatchDecision(
        route=DispatchRoute.TEMPORAL_DOCUMENT,
        source_type=source_type,
        mime_type=mime_type,
    )
