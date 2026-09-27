"""Unit tests for the Results and Documents read models.

Covers: literal (non-diagnostic) comparison against the printed reference range,
analyte grouping with an oldest-to-newest trend, thread linking restricted to
the caller's own threads, plain-language sources that never show ids, and the
derived plain-words document processing state.
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
from wellbe_contracts.records import DocumentStatus, RangePosition

_NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


@dataclass
class _Event:
    source_type: str = "manual_text"
    mime_type: str = "text/plain"
    source_metadata: dict[str, Any] = field(default_factory=lambda: {"capture_type": "lab"})
    captured_at: datetime = _NOW
    id: uuid.UUID = field(default_factory=uuid.uuid4)


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


def test_document_status_in_plain_words() -> None:
    status, label, _ = engine.document_status(added_at=_NOW, extracted_total=3, now=_NOW)
    assert (status, label) == (DocumentStatus.PROCESSED, "Processed")

    status, label, _ = engine.document_status(
        added_at=_NOW - timedelta(minutes=5), extracted_total=0, now=_NOW
    )
    assert (status, label) == (DocumentStatus.WAITING, "Waiting to be read")

    status, label, detail = engine.document_status(
        added_at=_NOW - timedelta(hours=2), extracted_total=0, now=_NOW
    )
    assert (status, label) == (DocumentStatus.COULD_NOT_READ, "Could not be read")
    assert "safely stored" in detail


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
