"""Original vault wording behind a memory, and dedupe of those texts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from wellbe_api.records.memory_sources import text_for_event
from wellbe_api.routers.phase5 import dedupe_memories
from wellbe_contracts.c13_api import MemoryEntryV2, MemorySourceTextV2

THREAD = str(uuid.uuid4())


def test_file_content_is_not_returned_as_raw_bytes() -> None:
    raw = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3 binary \x00\xff"
    label, text = text_for_event(source_type="pdf", original_filename="scan.pdf", content=raw)
    assert label == "File · scan.pdf"
    assert isinstance(text, str)
    assert "kept unchanged" in text
    assert "%PDF" not in text
    assert "\x00" not in text

    fallback_label, fallback_text = text_for_event(
        source_type="image", original_filename="  ", content=raw
    )
    assert fallback_label == "File"
    assert fallback_text == text


def test_manual_text_is_capped_and_published_case_line_is_the_label() -> None:
    body = "Published sample case C001: Dismissed\nSource: https://example.test\n\n" + ("x" * 9000)
    label, text = text_for_event(source_type="manual_text", original_filename=None, content=body)
    assert label == "Published sample case C001: Dismissed"
    assert len(text) == 8000
    assert text.startswith("Published sample case C001:")

    plain_label, plain = text_for_event(
        source_type="manual_text", original_filename=None, content="Just a note"
    )
    assert plain_label == "What you added"
    assert plain == "Just a note"

    result_label, result_text = text_for_event(
        source_type="manual_text",
        original_filename=None,
        content="LDL cholesterol: 168 mg/dL",
        capture_type="lab",
        test_name="LDL cholesterol",
    )
    assert result_label == "Result · LDL cholesterol"
    assert result_text == "LDL cholesterol: 168 mg/dL"

    reported_label, _reported = text_for_event(
        source_type="manual_text",
        original_filename=None,
        content="Morning cough",
        capture_type="symptom",
    )
    assert reported_label == "What you reported"

    note_label, _note = text_for_event(
        source_type="manual_text",
        original_filename=None,
        content="Ask about the cough",
        capture_type="note",
    )
    assert note_label == "Note"


def test_equal_timestamps_keep_both_source_texts_in_original_order() -> None:
    first_id, second_id = str(uuid.uuid4()), str(uuid.uuid4())
    when = datetime(2026, 9, 1, tzinfo=UTC)

    def entry(ref_id: str, label: str, body: str) -> MemoryEntryV2:
        return MemoryEntryV2(
            memory_entry_id=str(uuid.uuid4()),
            memory_type="clinical",
            lifecycle_state="visible",
            title="Pain",
            thread_id=THREAD,
            source_refs=[{"source_ref_type": "c4_extracted_fact", "source_ref_id": ref_id}],
            source_texts=[
                MemorySourceTextV2(
                    source_ref_type="c4_extracted_fact",
                    source_ref_id=ref_id,
                    label=label,
                    text=body,
                )
            ],
            created_at=when,
        )

    first = entry(first_id, "Published sample case C001: One", "alpha wording")
    second = entry(second_id, "Published sample case C002: Two", "beta wording")
    out = dedupe_memories([first, second])
    assert len(out) == 1
    assert [item.text for item in out[0].source_texts] == ["alpha wording", "beta wording"]
    assert [item.source_ref_id for item in out[0].source_texts] == [first_id, second_id]
    assert len(first.source_texts) == 1
