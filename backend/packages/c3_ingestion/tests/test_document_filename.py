"""Original filename handling: sanitised display name, never a path."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from wellbe_c3_ingestion.adapters.document import DocumentAdapter
from wellbe_contracts.c3_ingestion import (
    MAX_DISPLAY_FILENAME_CHARS,
    AdapterInput,
    NormalizedPayload,
    sanitize_display_filename,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("labs.pdf", "labs.pdf"),
        ("/etc/passwd", "passwd"),
        ("C:\\Users\\me\\Scans\\letter.pdf", "letter.pdf"),
        ("../../secret.pdf", "secret.pdf"),
        ("  Blood\t\ttest\n March .pdf ", "Blood test March .pdf"),
        ("bad\x00name\x1b.pdf", "badname.pdf"),
        ("rtl\u202etxt.pdf", "rtltxt.pdf"),
        ("..", None),
        ("", None),
        ("   ", None),
        ("folder/", None),
        (None, None),
        (42, None),
    ],
)
def test_sanitize_display_filename(raw: object, expected: str | None) -> None:
    assert sanitize_display_filename(raw) == expected


def test_long_names_are_capped_keeping_the_extension() -> None:
    name = sanitize_display_filename("a" * 500 + ".pdf")
    assert name is not None
    assert len(name) <= MAX_DISPLAY_FILENAME_CHARS
    assert name.endswith("….pdf")


def test_long_names_without_extension_are_capped() -> None:
    name = sanitize_display_filename("b" * 500)
    assert name is not None
    assert len(name) == MAX_DISPLAY_FILENAME_CHARS
    assert name.endswith("…")


async def test_document_adapter_moves_filename_to_provenance() -> None:
    adapter = DocumentAdapter()
    raw = AdapterInput.model_validate(
        {
            "source_type": "pdf",
            "raw_data": b"%PDF-1.4",
            "captured_at": datetime(2026, 9, 27, tzinfo=UTC),
            "actor_id": uuid.uuid4(),
            "patient_id": uuid.uuid4(),
            "metadata": {
                "capture_type": "document",
                "original_filename_hash": "abc",
                "original_filename": "/tmp/x/Letter.pdf",
            },
        }
    )
    payload = NormalizedPayload(data=b"%PDF-1.4", mime_type="application/pdf", byte_size=8)
    prov = await adapter.metadata(raw, payload)
    assert prov.original_filename == "Letter.pdf"
    assert prov.original_filename_hash == "abc"
    assert prov.source_metadata is not None
    assert "original_filename" not in prov.source_metadata
    assert prov.source_metadata["capture_type"] == "document"
