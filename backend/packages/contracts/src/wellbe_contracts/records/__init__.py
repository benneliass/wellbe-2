"""C13 personal records read contracts: Results and Documents.

Two calm, source-linked read models over the caller's own C2 raw captures and
C4 extracted facts:

- **Results** — lab / vital observations grouped by analyte, oldest-to-newest
  readings for a trend, the reference range exactly as the source gave it, and
  the Health Threads each analyte already belongs to. The only comparison made
  is a literal one against the printed reference range; it is never a
  normality verdict, never "abnormal", never a diagnosis.
- **Documents** — uploaded documents with type, date, a plain-words processing
  state, and what was extracted from each (counts by kind).

Every source is described by a human ``display_label``; ids are carried only so
clients can link, never for display.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class RangePosition(StrEnum):
    # The value sits inside the range printed with the result.
    WITHIN = "within"
    # The value sits outside the range printed with the result.
    OUTSIDE = "outside"
    # No range was given, or the value/range could not be compared literally.
    NOT_COMPARED = "not_compared"


class RecordSourceV2(BaseModel):
    # "entered_by_you" | "document" | "photo" | "connected_source"
    kind: str
    # Human label, e.g. "Entered by you" or "From a PDF you added".
    display_label: str
    # Raw capture this came from — for linking only, never displayed.
    capture_id: str
    # Set when the source is an uploaded document (links to Documents).
    document_id: str | None = None
    # C10 ReviewMarker value that honestly describes who stands behind it.
    review_marker: str


class ThreadRefV2(BaseModel):
    thread_id: str
    title: str


class ObservationV2(BaseModel):
    value: str
    unit: str | None = None
    # Numeric value when the reading is a single number (for trend alignment).
    numeric_value: float | None = None
    # Reference range exactly as provided by the source; never invented.
    reference_range: str | None = None
    range_position: RangePosition = RangePosition.NOT_COMPARED
    # Plain-language line describing ``range_position``.
    range_note: str
    observed_at: datetime
    source: RecordSourceV2


class AnalyteResultV2(BaseModel):
    # Stable grouping key for this analyte (e.g. "lab:ldl_cholesterol").
    analyte_key: str
    display_label: str
    # "lab" | "vital"
    kind: str
    latest: ObservationV2
    # Oldest to newest; includes ``latest`` as the final entry.
    history: list[ObservationV2] = Field(default_factory=list)
    threads: list[ThreadRefV2] = Field(default_factory=list)


class ResultsResponseV2(BaseModel):
    schema_version: Literal["c13.results.v2"] = "c13.results.v2"
    headline: str
    analytes: list[AnalyteResultV2] = Field(default_factory=list)
    note: str
    not_diagnosis: bool = True


class DocumentStatus(StrEnum):
    PROCESSED = "processed"
    WAITING = "waiting"
    COULD_NOT_READ = "could_not_read"


class ExtractedCountV2(BaseModel):
    # C4 fact type, e.g. "lab_result", "symptom".
    kind: str
    # Plain label, e.g. "lab results".
    label: str
    count: int


class DocumentV2(BaseModel):
    document_id: str
    display_label: str
    # Plain type, e.g. "PDF" or "Photo".
    type_label: str
    mime_type: str
    added_at: datetime
    status: DocumentStatus
    status_label: str
    status_detail: str
    extracted_total: int = 0
    extracted: list[ExtractedCountV2] = Field(default_factory=list)
    # Results (lab/vital) extracted from this document, for the results link.
    result_count: int = 0


class DocumentsResponseV2(BaseModel):
    schema_version: Literal["c13.documents.v2"] = "c13.documents.v2"
    headline: str
    documents: list[DocumentV2] = Field(default_factory=list)
    note: str


__all__ = [
    "AnalyteResultV2",
    "DocumentStatus",
    "DocumentV2",
    "DocumentsResponseV2",
    "ExtractedCountV2",
    "ObservationV2",
    "RangePosition",
    "RecordSourceV2",
    "ResultsResponseV2",
    "ThreadRefV2",
]
