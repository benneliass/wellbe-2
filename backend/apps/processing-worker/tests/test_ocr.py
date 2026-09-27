from __future__ import annotations

import io
import json
import shutil
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from PIL import Image, ImageDraw, ImageFont
from wellbe_c4_processing import ExtractionResult
from wellbe_c4_processing.extractor import parse_lab_lines
from wellbe_contracts.c4_processing import FactType, QualityFlag
from wellbe_processing_worker import ocr

LAB_LINES = ["Ferritin: 8 ng/mL (ref 15-150)", "Hemoglobin: 10.9 g/dL (ref 12-15.5)"]

needs_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract binary not installed"
)


def render_lab_image(lines: list[str] = LAB_LINES) -> Image.Image:
    font = ImageFont.load_default(size=56)
    image = Image.new("L", (1800, 140 + 110 * len(lines)), color=255)
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(lines):
        draw.text((80, 80 + 110 * i), line, fill=0, font=font)
    return image


def png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def image_pdf_bytes(image: Image.Image, pages: int = 1) -> bytes:
    buf = io.BytesIO()
    rgb = image.convert("RGB")
    rgb.save(buf, format="PDF", resolution=200.0, save_all=True, append_images=[rgb] * (pages - 1))
    return buf.getvalue()


def _result(confidence: float, flag: QualityFlag = QualityFlag.CLEAN) -> ExtractionResult:
    return ExtractionResult(
        fact_type=FactType.LAB_RESULT,
        entity_label="Ferritin",
        normalized_key="lab:ferritin:2026-09-27",
        extraction_confidence=confidence,
        quality_flag=flag,
        quality_metadata={"method": "structured_capture"},
    )


# ------------------------------------------------------------ pure helpers


def test_parse_tsv_rebuilds_lines_and_confidences() -> None:
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tl\tt\tw\th\tconf\ttext"
    rows = [
        "1\t1\t0\t0\t0\t0\t0\t0\t10\t10\t-1\t",
        "5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t96.0\tFerritin:",
        "5\t1\t1\t1\t1\t2\t0\t0\t10\t10\t90\t8",
        "5\t1\t1\t1\t2\t1\t0\t0\t10\t10\t80.5\tHemoglobin:",
        "5\t1\t1\t1\t2\t2\t0\t0\t10\t10\t70\t ",
    ]
    text, confs = ocr._parse_tsv("\n".join([header, *rows]))
    assert text == "Ferritin: 8\nHemoglobin:"
    assert confs == pytest.approx([0.96, 0.90, 0.805])


def test_has_usable_text_threshold() -> None:
    assert not ocr.has_usable_text("Page 1 of 2 — scan")
    assert ocr.has_usable_text(LAB_LINES[0])


def test_apply_ocr_provenance_scales_floors_and_never_improves_flag() -> None:
    prov = {"extractor": "ocr-tesseract-5.5.0", "mean_confidence": 0.9, "pages": 1}
    clean, weak, review = ocr.apply_ocr_provenance(
        [_result(0.97), _result(0.4), _result(0.95, QualityFlag.REQUIRES_REVIEW)], prov
    )
    assert clean.extraction_confidence == pytest.approx(0.873)
    assert clean.quality_flag == QualityFlag.CLEAN
    assert clean.quality_metadata["text_source"] == "ocr"
    assert clean.quality_metadata["ocr"]["extractor"] == "ocr-tesseract-5.5.0"
    assert clean.quality_metadata["pre_ocr_confidence"] == 0.97
    assert clean.quality_metadata["method"] == "structured_capture"
    assert weak.extraction_confidence == pytest.approx(0.36)
    assert review.quality_flag == QualityFlag.REQUIRES_REVIEW

    (floored,) = ocr.apply_ocr_provenance([_result(0.97)], {"mean_confidence": 0.1})
    assert floored.extraction_confidence == ocr.OCR_CONFIDENCE_FLOOR
    assert floored.quality_flag == QualityFlag.REQUIRES_REVIEW
    (low,) = ocr.apply_ocr_provenance([_result(0.2)], {"mean_confidence": 0.5})
    assert low.extraction_confidence == pytest.approx(0.2)


# ------------------------------------------------------------------ limits


def test_oversized_document_is_rejected_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr, "MAX_DOCUMENT_BYTES", 1024)
    content = png_bytes(render_lab_image())
    assert len(content) > 1024
    with pytest.raises(ocr.OcrRejectedError, match="max 1024"):
        ocr.ocr_document(content)
    assert ocr.extract_document_text_sync(content) == ocr.DocumentText("")


def test_too_many_pages_is_rejected_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr, "tesseract_version", lambda: "test")
    monkeypatch.setattr(ocr, "MAX_PAGES", 3)
    content = image_pdf_bytes(Image.new("L", (200, 200), 255), pages=4)
    with pytest.raises(ocr.OcrRejectedError, match="4 pages"):
        ocr.ocr_document(content)
    assert ocr.extract_document_text_sync(content) == ocr.DocumentText("")


def test_oversized_image_pixels_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr, "tesseract_version", lambda: "test")
    monkeypatch.setattr(ocr, "MAX_IMAGE_PIXELS", 100 * 100)
    with pytest.raises(ocr.OcrRejectedError, match="px"):
        ocr.ocr_document(png_bytes(Image.new("L", (200, 200), 255)))


def test_unreadable_input_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr, "tesseract_version", lambda: "test")
    with pytest.raises(ocr.OcrRejectedError, match="not a readable image"):
        ocr.ocr_document(b"definitely not an image")
    with pytest.raises(ocr.OcrRejectedError, match="unreadable PDF"):
        ocr.ocr_document(b"%PDF-1.4 truncated garbage")


def test_missing_tesseract_leaves_text_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr, "tesseract_version", lambda: None)
    assert ocr.extract_document_text_sync(png_bytes(render_lab_image())).text == ""


def test_text_layer_pdf_skips_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_: bytes) -> ocr.OcrResult:
        raise AssertionError("OCR must not run for a digital PDF")

    monkeypatch.setattr(ocr, "ocr_document", boom)
    monkeypatch.setattr(ocr, "pdf_text_layer", lambda _: "Vitamin B12: 180 pg/mL (ref 200-900)")
    doc = ocr.extract_document_text_sync(b"%PDF-1.4 ...")
    assert doc.ocr is None
    assert "B12" in doc.text


def _fake_ocr(text: str) -> Any:
    return lambda _: ocr.OcrResult(text, 1, 0.9, "ocr-tesseract-test", 5)


def test_ocr_yielding_nothing_warns_and_keeps_text_layer(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(ocr, "pdf_text_layer", lambda _: "")
    monkeypatch.setattr(ocr, "ocr_document", _fake_ocr("  \n "))
    assert ocr.extract_document_text_sync(b"%PDF-1.4 ...", "evt") == ocr.DocumentText("")
    assert "OCR yielded no text" in caplog.text


def test_short_text_layer_kept_when_ocr_finds_no_more(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr, "pdf_text_layer", lambda _: "Folate: 2.1 ng/mL")
    monkeypatch.setattr(ocr, "ocr_document", _fake_ocr("Folate 2.1"))
    assert ocr.extract_document_text_sync(b"%PDF-1.4 ...") == ocr.DocumentText(
        "Folate: 2.1 ng/mL"
    )
    monkeypatch.setattr(ocr, "ocr_document", _fake_ocr("Folate: 2.1 ng/mL (ref 3-17)"))
    doc = ocr.extract_document_text_sync(b"%PDF-1.4 ...")
    assert doc.ocr is not None and "ref 3-17" in doc.text


# ------------------------------------------------------------- tesseract


@needs_tesseract
def test_ocr_png_reads_lab_lines() -> None:
    doc = ocr.extract_document_text_sync(png_bytes(render_lab_image()))
    assert doc.ocr is not None
    assert doc.ocr.engine.startswith("ocr-tesseract-")
    assert doc.ocr.pages == 1
    assert doc.ocr.mean_confidence > 0.7
    assert "Ferritin: 8 ng/mL" in doc.text
    assert "Hemoglobin: 10.9 g/dL" in doc.text
    labs = {lab["test_name"]: lab for lab in parse_lab_lines(doc.text)}
    assert labs["Ferritin"]["value"] == "8"
    assert labs["Ferritin"]["reference_range"] == "15-150"
    assert labs["Hemoglobin"]["value"] == "10.9"
    assert labs["Hemoglobin"]["reference_range"] == "12-15.5"


@needs_tesseract
def test_ocr_image_only_pdf() -> None:
    content = image_pdf_bytes(render_lab_image())
    assert ocr.pdf_text_layer(content) == ""
    doc = ocr.extract_document_text_sync(content)
    assert doc.ocr is not None
    assert {lab["test_name"] for lab in parse_lab_lines(doc.text)} == {"Ferritin", "Hemoglobin"}


@needs_tesseract
def test_ocr_applies_exif_orientation() -> None:
    rotated = render_lab_image().rotate(90, expand=True)
    exif = Image.Exif()
    exif[0x0112] = 6  # display needs a 90° clockwise turn
    buf = io.BytesIO()
    rotated.convert("RGB").save(buf, format="JPEG", quality=95, exif=exif)
    doc = ocr.extract_document_text_sync(buf.getvalue())
    assert "Ferritin" in doc.text


@needs_tesseract
def test_ocr_heic_photo() -> None:
    pillow_heif = pytest.importorskip("pillow_heif")
    pillow_heif.register_heif_opener()
    buf = io.BytesIO()
    try:
        render_lab_image().convert("RGB").save(buf, format="HEIF", quality=90)
    except (KeyError, OSError, ValueError) as exc:
        pytest.skip(f"HEIF encoder unavailable: {exc}")
    doc = ocr.extract_document_text_sync(buf.getvalue())
    assert "Ferritin" in doc.text


@needs_tesseract
async def test_async_wrapper_runs_off_loop() -> None:
    doc = await ocr.extract_document_text(png_bytes(render_lab_image()), "evt")
    assert "Hemoglobin" in doc.text


# ------------------------------------------------------ pipeline integration


class _FakeSession:
    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self) -> None:
        return None


def _vault_event(mime_type: str) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid.uuid4()),
        "patient_id": str(uuid.uuid4()),
        "actor_id": str(uuid.uuid4()),
        "source_type": "pdf",
        "idempotency_key": "k",
        "captured_at": now,
        "received_at": now,
        "ingested_at": now,
        "content_hash": "h",
        "blob_ref": "vault/raw/blob",
        "byte_size": 1,
        "mime_type": mime_type,
        "source_metadata": {"capture_type": "document"},
        "adapter_name": "wellbe-document",
        "adapter_version": "0.1.0",
        "ingestor_version": "0.1.0",
        "consent_snapshot_id": str(uuid.uuid4()),
        "encryption_key_id": "k",
        "encryption_key_version": 1,
        "correlation_id": "c",
        "trace_id": "t",
        "created_at": now,
    }


@needs_tesseract
@pytest.mark.parametrize("mime_type", ["image/png", "application/pdf"])
async def test_pipeline_extracts_ocr_labs_with_provenance(
    monkeypatch: pytest.MonkeyPatch, mime_type: str
) -> None:
    import wellbe_c4_processing
    import wellbe_c5_evidence
    import wellbe_db
    import wellbe_events
    from wellbe_processing_worker import tasks

    inserted: list[dict[str, Any]] = []
    linked: list[dict[str, Any]] = []

    class FakeRepo:
        def __init__(self, session: object) -> None: ...

        async def insert_fact(self, **kw: Any) -> uuid.UUID:
            inserted.append(kw)
            return uuid.UUID(str(kw["id"]))

    class FakeEvidence:
        def __init__(self, session: object) -> None: ...

        async def link_fact(self, **kw: Any) -> None:
            linked.append(kw)

    async def noop(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(wellbe_db, "create_engine", lambda url: None)
    monkeypatch.setattr(wellbe_db, "create_session_factory", lambda engine: _FakeSession)
    monkeypatch.setattr(wellbe_c4_processing, "ProcessingRepository", FakeRepo)
    monkeypatch.setattr(wellbe_c5_evidence, "EvidenceService", FakeEvidence)
    monkeypatch.setattr(wellbe_events, "emit_event", noop)
    monkeypatch.setattr(tasks, "_create_graph_node", noop)
    monkeypatch.setattr(tasks, "_link_co_occurrence", noop)
    monkeypatch.setattr(tasks, "_emit_genesis_input_ready", noop)

    # What the dispatch loop does after GET /vault/events/{id}/content.
    image = render_lab_image()
    content = png_bytes(image) if mime_type == "image/png" else image_pdf_bytes(image)
    vault_event = _vault_event(mime_type)
    document = await ocr.extract_document_text(content, vault_event["id"])
    assert document.ocr is not None
    vault_event["_raw_text"] = document.text
    vault_event["_ocr"] = document.ocr.provenance()

    await tasks._extract_facts(json.dumps(vault_event))

    labs = {f["entity_label"]: f for f in inserted if f["fact_type"] == "lab_result"}
    assert set(labs) == {"Ferritin", "Hemoglobin"}
    ocr_conf = document.ocr.mean_confidence
    for fact in labs.values():
        meta = fact["quality_metadata"]
        assert meta["text_source"] == "ocr"
        assert meta["ocr"]["extractor"] == document.ocr.engine
        assert meta["ocr"]["mean_confidence"] == pytest.approx(ocr_conf, abs=1e-3)
        assert fact["extraction_confidence"] < 0.97
        assert fact["extraction_confidence"] == pytest.approx(
            max(0.3, 0.97 * round(ocr_conf, 3)), abs=1e-3
        )
    assert labs["Ferritin"]["quality_metadata"]["raw_value"] == "8"
    assert all(link["evidence_refs"][0].confidence < 0.97 for link in linked)
