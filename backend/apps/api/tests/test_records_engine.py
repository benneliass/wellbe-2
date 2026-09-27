"""Unit tests for the Results and Documents read models.

Covers: literal (non-diagnostic) comparison against the printed reference range,
analyte grouping with an oldest-to-newest trend, thread linking restricted to
the caller's own threads, plain-language sources that never show ids, and the
stored (or, for older rows, derived) plain-words document processing state and
the original filename with its fallback label.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from wellbe_api.main import app
from wellbe_api.records import engine
from wellbe_contracts.records import DocumentProcessingStatus, DocumentStatus, RangePosition

_NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


@dataclass
class _Event:
    source_type: str = "manual_text"
    mime_type: str = "text/plain"
    source_metadata: dict[str, Any] = field(default_factory=lambda: {"capture_type": "lab"})
    captured_at: datetime = _NOW
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    original_filename: str | None = None


@dataclass
class _Fact:
    raw_context_event_id: uuid.UUID
    captured_at: datetime
    raw_value: str
    raw_test_name: str = "LDL cholesterol"
    fact_type: str = "lab_result"
    unit: str | None = "mg/dL"
    reference_range: str | None = "<130"
    normalized_key: str = ""
    entity_label: str = ""

    def __post_init__(self) -> None:
        self.entity_label = self.entity_label or self.raw_test_name
        if not self.normalized_key:
            slug = self.raw_test_name.lower().replace(" ", "_")
            kind = "vital" if self.fact_type == "vital_sign" else "lab"
            self.normalized_key = f"{kind}:{slug}:{self.captured_at.date().isoformat()}"

    @property
    def quality_metadata(self) -> dict[str, Any]:
        return {
            "raw_test_name": self.raw_test_name,
            "raw_value": self.raw_value,
            "raw_unit": self.unit,
            "reference_range": self.reference_range,
        }


@pytest.mark.parametrize(
    ("value", "ref", "expected"),
    [
        ("22", "30-100", RangePosition.OUTSIDE),
        ("45", "30-100", RangePosition.WITHIN),
        ("30", "30 – 100", RangePosition.WITHIN),
        ("5.4", "4.0-5.6", RangePosition.WITHIN),
        ("165", "<130", RangePosition.OUTSIDE),
        ("129", "<130", RangePosition.WITHIN),
        ("130", "<=130", RangePosition.WITHIN),
        ("60", ">40", RangePosition.WITHIN),
        ("128/82", "<120/80", RangePosition.OUTSIDE),
        ("110/70", "<120/80", RangePosition.WITHIN),
        ("positive", "negative", RangePosition.NOT_COMPARED),
        ("<0.5", "0-1", RangePosition.NOT_COMPARED),
        ("12", None, RangePosition.NOT_COMPARED),
        ("12", "see note", RangePosition.NOT_COMPARED),
        ("12", "100-10", RangePosition.NOT_COMPARED),
    ],
)
def test_compare_to_range_is_literal(value: str, ref: str | None, expected: RangePosition) -> None:
    assert engine.compare_to_range(value, ref) is expected


def test_range_notes_are_calm_and_never_diagnostic() -> None:
    notes = [
        engine.range_note(RangePosition.OUTSIDE, "<130"),
        engine.range_note(RangePosition.WITHIN, "<130"),
        engine.range_note(RangePosition.NOT_COMPARED, "see note"),
        engine.range_note(RangePosition.NOT_COMPARED, None),
    ]
    assert notes[0] == "Outside the reference range shown on the report"
    for note in notes:
        lowered = note.lower()
        assert "abnormal" not in lowered
        assert "diagnos" not in lowered


def test_results_group_by_analyte_with_trend_and_thread_link() -> None:
    ev_old, ev_new = _Event(), _Event()
    other_ev = _Event()
    old = _Fact(ev_old.id, _NOW - timedelta(days=90), "150")
    new = _Fact(ev_new.id, _NOW, "165")
    vit_d = _Fact(
        other_ev.id,
        _NOW - timedelta(days=1),
        "22",
        raw_test_name="Vitamin D",
        unit="ng/mL",
        reference_range="30-100",
    )
    thread_id = uuid.uuid4()
    foreign_thread = uuid.uuid4()

    result = engine.build_results(
        facts=[new, vit_d, old],
        events={e.id: e for e in (ev_old, ev_new, other_ev)},
        node_threads={new.normalized_key: [thread_id, foreign_thread]},
        thread_titles={thread_id: "LDL cholesterol"},
    )

    assert [a.display_label for a in result.analytes] == ["LDL cholesterol", "Vitamin D"]
    ldl = result.analytes[0]
    assert ldl.analyte_key == "lab:ldl_cholesterol"
    assert [o.value for o in ldl.history] == ["150", "165"]
    assert ldl.latest.value == "165"
    assert ldl.latest.numeric_value == 165.0
    assert ldl.latest.range_position is RangePosition.OUTSIDE
    # Only the caller's own threads (known titles) are linked.
    assert [(t.thread_id, t.title) for t in ldl.threads] == [(str(thread_id), "LDL cholesterol")]
    assert result.analytes[1].threads == []
    assert result.not_diagnosis is True


def test_results_link_thread_from_capture_metadata() -> None:
    thread_id = uuid.uuid4()
    ev = _Event(source_metadata={"capture_type": "lab", "thread_id": str(thread_id)})
    fact = _Fact(
        ev.id, _NOW, "5.4", raw_test_name="Hemoglobin A1c", unit="%", reference_range="4.0-5.6"
    )
    result = engine.build_results(
        facts=[fact],
        events={ev.id: ev},
        node_threads={},
        thread_titles={thread_id: "Energy dips"},
    )
    assert result.analytes[0].threads[0].title == "Energy dips"


def test_sources_are_plain_language_and_carry_no_visible_id() -> None:
    manual = engine.source_for(_Event())
    assert manual.display_label == "Entered by you"
    assert manual.review_marker == "patient-entered"
    assert manual.document_id is None

    pdf_ev = _Event(
        source_type="pdf",
        mime_type="application/pdf",
        source_metadata={"capture_type": "document", "source": "City Lab"},
    )
    pdf = engine.source_for(pdf_ev)
    assert pdf.display_label == "From a PDF you added · City Lab"
    assert pdf.document_id == str(pdf_ev.id)
    assert str(pdf_ev.id) not in pdf.display_label
    assert pdf.review_marker == "not-clinician-reviewed"


def test_empty_results_are_calm() -> None:
    result = engine.build_results(facts=[], events={}, node_threads={}, thread_titles={})
    assert result.analytes == []
    assert result.headline == "No results yet"


def test_facts_without_a_capture_are_skipped() -> None:
    fact = _Fact(uuid.uuid4(), _NOW, "1")
    result = engine.build_results(facts=[fact], events={}, node_threads={}, thread_titles={})
    assert result.analytes == []


def test_document_status_derived_for_rows_without_a_stored_status() -> None:
    ps, status, label, _ = engine.document_status(added_at=_NOW, extracted_total=3, now=_NOW)
    assert (ps, status, label) == (
        DocumentProcessingStatus.PROCESSED,
        DocumentStatus.PROCESSED,
        "Processed",
    )

    ps, status, label, _ = engine.document_status(
        added_at=_NOW - timedelta(minutes=5), extracted_total=0, now=_NOW
    )
    assert (ps, status, label) == (
        DocumentProcessingStatus.RECEIVED,
        DocumentStatus.WAITING,
        "Received",
    )

    ps, status, label, detail = engine.document_status(
        added_at=_NOW - timedelta(hours=2), extracted_total=0, now=_NOW
    )
    assert (ps, status, label) == (
        DocumentProcessingStatus.NEEDS_OCR,
        DocumentStatus.COULD_NOT_READ,
        "Could not be read",
    )
    assert "safely stored" in detail


@pytest.mark.parametrize(
    ("stored", "expected", "legacy", "label"),
    [
        ("received", DocumentProcessingStatus.RECEIVED, DocumentStatus.WAITING, "Received"),
        ("processing", DocumentProcessingStatus.PROCESSING, DocumentStatus.WAITING, "Being read"),
        ("processed", DocumentProcessingStatus.PROCESSED, DocumentStatus.PROCESSED, "Processed"),
        (
            "needs_ocr",
            DocumentProcessingStatus.NEEDS_OCR,
            DocumentStatus.COULD_NOT_READ,
            "Could not be read",
        ),
        (
            "failed",
            DocumentProcessingStatus.FAILED,
            DocumentStatus.COULD_NOT_READ,
            "Couldn't finish reading",
        ),
    ],
)
def test_stored_status_is_authoritative_over_the_time_window(
    stored: str,
    expected: DocumentProcessingStatus,
    legacy: DocumentStatus,
    label: str,
) -> None:
    old = _NOW - timedelta(days=3)
    ps, status, got_label, detail = engine.document_status(
        added_at=old, extracted_total=0, now=_NOW, stored=stored
    )
    assert (ps, status, got_label) == (expected, legacy, label)
    assert detail


def test_facts_mean_processed_even_if_stored_status_lags() -> None:
    ps, status, _, detail = engine.document_status(
        added_at=_NOW, extracted_total=2, now=_NOW, stored="failed"
    )
    assert ps is DocumentProcessingStatus.PROCESSED
    assert status is DocumentStatus.PROCESSED
    assert "found 2 things" in detail


def test_unknown_stored_status_falls_back_to_derivation() -> None:
    ps, *_ = engine.document_status(
        added_at=_NOW - timedelta(hours=2), extracted_total=0, now=_NOW, stored="bogus"
    )
    assert ps is DocumentProcessingStatus.NEEDS_OCR


def test_needs_ocr_detail_explains_missing_text_recognition() -> None:
    *_, detail = engine.document_status(
        added_at=_NOW,
        extracted_total=0,
        now=_NOW,
        stored="needs_ocr",
        stored_detail="ocr_unavailable",
    )
    assert "text recognition" in detail


def test_status_copy_is_calm() -> None:
    for stored in ("received", "processing", "processed", "needs_ocr", "failed"):
        _, _, label, detail = engine.document_status(
            added_at=_NOW, extracted_total=0, now=_NOW, stored=stored
        )
        text = f"{label} {detail}".lower()
        assert "!" not in text
        assert not any(w in text for w in ("error", "urgent", "warning", "corrupt"))


def test_original_filename_shown_with_fallback_label_kept() -> None:
    named = _Event(
        source_type="pdf",
        mime_type="application/pdf",
        source_metadata={"capture_type": "document", "source": "Clinic"},
        original_filename="Blood test — March.pdf",
    )
    legacy = _Event(
        source_type="pdf",
        mime_type="application/pdf",
        source_metadata={"capture_type": "document"},
        captured_at=_NOW - timedelta(minutes=1),
    )
    result = engine.build_documents(
        events=[named, legacy],
        fact_counts={},
        stored_statuses={named.id: ("processing", None)},
        now=_NOW,
    )
    first, second = result.documents
    assert first.original_filename == "Blood test — March.pdf"
    assert first.display_label == "PDF document from Clinic"
    assert first.processing_status is DocumentProcessingStatus.PROCESSING
    assert second.original_filename is None
    assert second.display_label == "PDF document"
    assert second.processing_status is DocumentProcessingStatus.RECEIVED


def test_stored_filename_is_re_sanitised_on_read() -> None:
    event = _Event(
        source_type="pdf",
        mime_type="application/pdf",
        source_metadata={"capture_type": "document"},
        original_filename="C:\\Users\\me\\scan\x00.pdf",
    )
    (doc,) = engine.build_documents(events=[event], fact_counts={}, now=_NOW).documents
    assert doc.original_filename == "scan.pdf"


def test_build_documents_counts_extractions_and_results() -> None:
    pdf = _Event(
        source_type="pdf",
        mime_type="application/pdf",
        source_metadata={"capture_type": "document"},
        captured_at=_NOW - timedelta(days=1),
    )
    photo = _Event(
        source_type="photo",
        mime_type="image/jpeg",
        source_metadata={"capture_type": "document"},
        captured_at=_NOW - timedelta(hours=3),
    )
    result = engine.build_documents(
        events=[pdf, photo],
        fact_counts={pdf.id: {"lab_result": 3, "symptom": 1}},
        now=_NOW,
    )
    first, second = result.documents
    assert first.document_id == str(photo.id)
    assert first.type_label == "Photo"
    assert first.status is DocumentStatus.COULD_NOT_READ
    assert first.processing_status is DocumentProcessingStatus.NEEDS_OCR
    assert second.display_label == "PDF document"
    assert second.status is DocumentStatus.PROCESSED
    assert second.extracted_total == 4
    assert second.result_count == 3
    assert [(c.kind, c.label, c.count) for c in second.extracted] == [
        ("lab_result", "lab results", 3),
        ("symptom", "symptom", 1),
    ]


def test_empty_documents_are_calm() -> None:
    result = engine.build_documents(events=[], fact_counts={}, now=_NOW)
    assert result.headline == "No documents yet"


def test_records_routes_are_registered() -> None:
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert "get" in paths["/v2/results"]
    assert "get" in paths["/v2/documents"]
