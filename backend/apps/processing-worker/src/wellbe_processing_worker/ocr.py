"""Local OCR for image-only documents (scanned PDFs, photos) via the Tesseract CLI.

Health data must never leave the homeserver: PDF rendering (pypdfium2), image
preparation (Pillow) and recognition (a ``tesseract`` subprocess) all run inside
the worker container. No network calls are made here.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import logging
import os
import re
import shutil
import subprocess
import time
from collections.abc import Generator
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Any

import pypdfium2 as pdfium
from PIL import Image, ImageOps, ImageSequence, UnidentifiedImageError
from wellbe_c4_processing import ExtractionResult, compute_quality_flag
from wellbe_contracts.c4_processing import QualityFlag

logger = logging.getLogger("wellbe.processing_worker.ocr")

LANGUAGE = "eng"
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
MAX_PAGES = 20
PAGE_TIMEOUT_SECONDS = 60.0
# Wall-clock budget for one document; remaining pages are skipped once exceeded.
DOCUMENT_BUDGET_SECONDS = 300.0
RENDER_DPI = 300
MAX_RENDER_SIDE_PX = 5000
MAX_IMAGE_PIXELS = 50_000_000
# Tesseract reads best at ~30px x-height; small photos/screenshots are upscaled.
MIN_OCR_SIDE_PX = 1500
MAX_UPSCALE = 3.0
# A text layer with fewer alphanumerics than this is treated as absent (scanner
# stamps, page numbers) and the document is OCR'd instead.
MIN_MEANINGFUL_CHARS = 20
OCR_CONFIDENCE_FLOOR = 0.3

_OCR_SEMAPHORE = asyncio.Semaphore(1)
_FLAG_SEVERITY = {
    QualityFlag.CLEAN: 0,
    QualityFlag.LOW_CONFIDENCE: 1,
    QualityFlag.REQUIRES_REVIEW: 2,
    QualityFlag.PARTIAL: 3,
}


class OcrRejectedError(Exception):
    """The input exceeds OCR limits or is not a readable PDF/image."""


@dataclass(frozen=True)
class OcrResult:
    text: str
    pages: int
    mean_confidence: float
    engine: str
    elapsed_ms: int

    def provenance(self) -> dict[str, Any]:
        return {
            "extractor": self.engine,
            "mean_confidence": round(self.mean_confidence, 3),
            "pages": self.pages,
            "chars": len(self.text),
        }


@dataclass(frozen=True)
class DocumentText:
    text: str
    ocr: OcrResult | None = None


def meaningful_chars(text: str) -> int:
    return sum(ch.isalnum() for ch in text)


def has_usable_text(text: str) -> bool:
    return meaningful_chars(text) >= MIN_MEANINGFUL_CHARS


@lru_cache(maxsize=1)
def tesseract_version() -> str | None:
    """Installed tesseract version, or None when the binary is unavailable."""
    binary = shutil.which("tesseract")
    if binary is None:
        return None
    try:
        proc = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"tesseract\s+v?(\d+(?:\.\d+)*)", proc.stdout + proc.stderr)
    return match.group(1) if match else "unknown"


def engine_name() -> str:
    return f"ocr-tesseract-{tesseract_version() or 'unavailable'}"


def is_pdf_bytes(content: bytes) -> bool:
    return b"%PDF-" in content[:1024]


def pdf_text_layer(content: bytes) -> str:
    """Text layer of a digital PDF ("" for image-only/unreadable documents)."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception:
        logger.warning("could not read PDF text layer", exc_info=True)
        return ""


# --------------------------------------------------------------------- pages


def _pdf_pages(content: bytes) -> tuple[int, Generator[Image.Image]]:
    try:
        pdf = pdfium.PdfDocument(content)
    except pdfium.PdfiumError as exc:
        raise OcrRejectedError(f"unreadable PDF: {exc}") from exc
    count = len(pdf)
    if count > MAX_PAGES:
        pdf.close()
        raise OcrRejectedError(f"PDF has {count} pages (max {MAX_PAGES})")

    def render() -> Generator[Image.Image]:
        try:
            for index in range(count):
                page = pdf[index]
                try:
                    width, height = page.get_size()
                    scale = min(RENDER_DPI / 72, MAX_RENDER_SIDE_PX / max(width, height, 1.0))
                    yield page.render(scale=scale, grayscale=True).to_pil()
                finally:
                    page.close()
        finally:
            pdf.close()

    return count, render()


def _register_heif() -> None:
    with contextlib.suppress(ImportError):
        from pillow_heif import register_heif_opener

        register_heif_opener()


def _image_pages(content: bytes) -> tuple[int, Generator[Image.Image]]:
    _register_heif()
    try:
        image = Image.open(io.BytesIO(content))
    except (UnidentifiedImageError, OSError) as exc:
        raise OcrRejectedError(f"not a readable image: {exc}") from exc
    width, height = image.size
    if width * height > MAX_IMAGE_PIXELS:
        raise OcrRejectedError(f"image is {width}x{height} px (max {MAX_IMAGE_PIXELS} pixels)")
    count = int(getattr(image, "n_frames", 1))
    if count > MAX_PAGES:
        raise OcrRejectedError(f"image has {count} frames (max {MAX_PAGES})")

    def frames() -> Generator[Image.Image]:
        for frame in ImageSequence.Iterator(image):
            yield ImageOps.exif_transpose(frame)

    return count, frames()


def _prepare(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA", "P", "PA"):
        rgba = image.convert("RGBA")
        image = Image.new("RGB", rgba.size, "white")
        image.paste(rgba, mask=rgba.getchannel("A"))
    gray = image.convert("L")
    longest = max(gray.size)
    if 0 < longest < MIN_OCR_SIDE_PX:
        factor = min(MAX_UPSCALE, MIN_OCR_SIDE_PX / longest)
        size = (round(gray.width * factor), round(gray.height * factor))
        gray = gray.resize(size, Image.Resampling.LANCZOS)
    return gray


# --------------------------------------------------------------- recognition


def _parse_tsv(tsv: str) -> tuple[str, list[float]]:
    """Rebuild line text and collect word confidences (0..1) from tesseract TSV."""
    lines: dict[tuple[str, ...], list[str]] = {}
    confidences: list[float] = []
    for row in tsv.splitlines()[1:]:
        cols = row.split("\t")
        if len(cols) < 12 or not cols[11].strip():
            continue
        try:
            conf = float(cols[10])
        except ValueError:
            continue
        if conf < 0:
            continue
        lines.setdefault(tuple(cols[1:5]), []).append(cols[11].strip())
        confidences.append(min(conf, 100.0) / 100.0)
    return "\n".join(" ".join(words) for words in lines.values()), confidences


def _tesseract(image: Image.Image, timeout: float) -> tuple[str, list[float]]:
    binary = shutil.which("tesseract")
    if binary is None:
        raise OcrRejectedError("tesseract binary not installed")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    try:
        proc = subprocess.run(
            [binary, "stdin", "stdout", "-l", LANGUAGE, "--psm", "3", "tsv"],
            input=buf.getvalue(),
            capture_output=True,
            timeout=timeout,
            check=False,
            # One document at a time already; keep tesseract from fanning out
            # OpenMP threads across every core of the shared node.
            env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        )
    except subprocess.TimeoutExpired:
        logger.warning("tesseract page timed out after %.0fs; page skipped", timeout)
        return "", []
    if proc.returncode != 0:
        logger.warning(
            "tesseract exited %s; page skipped: %s",
            proc.returncode,
            proc.stderr.decode("utf-8", errors="replace")[:200],
        )
        return "", []
    return _parse_tsv(proc.stdout.decode("utf-8", errors="replace"))


def _ocr_pages(pages: Generator[Image.Image], total: int) -> OcrResult:
    start = time.monotonic()
    texts: list[str] = []
    confidences: list[float] = []
    done = 0
    with contextlib.closing(pages) as page_iter:
        for page in page_iter:
            remaining = DOCUMENT_BUDGET_SECONDS - (time.monotonic() - start)
            if remaining <= 0:
                logger.warning(
                    "OCR budget of %.0fs exhausted after %d/%d page(s)",
                    DOCUMENT_BUDGET_SECONDS,
                    done,
                    total,
                )
                break
            text, page_conf = _tesseract(_prepare(page), min(PAGE_TIMEOUT_SECONDS, remaining))
            done += 1
            if text.strip():
                texts.append(text.strip())
            confidences.extend(page_conf)
    return OcrResult(
        text="\n\n".join(texts),
        pages=done,
        mean_confidence=sum(confidences) / len(confidences) if confidences else 0.0,
        engine=engine_name(),
        elapsed_ms=round((time.monotonic() - start) * 1000),
    )


def ocr_document(content: bytes) -> OcrResult:
    """OCR every page of a PDF or image. Raises OcrRejectedError past the limits."""
    if len(content) > MAX_DOCUMENT_BYTES:
        raise OcrRejectedError(
            f"document is {len(content)} bytes (max {MAX_DOCUMENT_BYTES})"
        )
    if tesseract_version() is None:
        raise OcrRejectedError("tesseract binary not installed")
    total, pages = _pdf_pages(content) if is_pdf_bytes(content) else _image_pages(content)
    return _ocr_pages(pages, total)


def extract_document_text_sync(content: bytes, event_id: object = None) -> DocumentText:
    """Text for a document: the PDF text layer when usable, otherwise local OCR.

    Never raises: a document that cannot be read yields empty text (the raw blob
    stays in the vault for a later backfill) instead of a poison-pill retry loop.
    """
    text_layer = pdf_text_layer(content) if is_pdf_bytes(content) else ""
    if has_usable_text(text_layer):
        logger.info(
            "document %s: %d bytes, text layer %d chars", event_id, len(content), len(text_layer)
        )
        return DocumentText(text_layer)
    try:
        result = ocr_document(content)
    except OcrRejectedError as exc:
        logger.warning("document %s not OCR'd: %s", event_id, exc)
        return DocumentText(text_layer)
    except Exception:
        logger.exception("document %s: OCR failed", event_id)
        return DocumentText(text_layer)

    if meaningful_chars(result.text) == 0:
        logger.warning(
            "document %s: OCR yielded no text (pages=%d, ms=%d, engine=%s)",
            event_id,
            result.pages,
            result.elapsed_ms,
            result.engine,
        )
        return DocumentText(text_layer)
    if meaningful_chars(result.text) <= meaningful_chars(text_layer):
        logger.info(
            "document %s: short text layer kept (%d chars); OCR found no more",
            event_id,
            len(text_layer),
        )
        return DocumentText(text_layer)
    logger.info(
        "document %s OCR: pages=%d chars=%d mean_confidence=%.2f ms=%d engine=%s",
        event_id,
        result.pages,
        len(result.text),
        result.mean_confidence,
        result.elapsed_ms,
        result.engine,
    )
    return DocumentText(result.text, result)


async def extract_document_text(content: bytes, event_id: object = None) -> DocumentText:
    """Async wrapper: OCR is CPU-bound, so run it off-loop, one document at a time."""
    async with _OCR_SEMAPHORE:
        return await asyncio.to_thread(extract_document_text_sync, content, event_id)


# ---------------------------------------------------------------- provenance


def apply_ocr_provenance(
    results: list[ExtractionResult], ocr: dict[str, Any]
) -> list[ExtractionResult]:
    """Mark facts as OCR-derived and weaken their confidence by the OCR confidence.

    ``confidence * ocr_mean_confidence``, floored at ``OCR_CONFIDENCE_FLOOR`` (the
    floor never raises a confidence that was already below it). The quality flag
    is recomputed but never improved.
    """
    ocr_conf = max(0.0, min(1.0, float(ocr.get("mean_confidence") or 0.0)))
    adjusted: list[ExtractionResult] = []
    for result in results:
        original = result.extraction_confidence
        confidence = round(
            max(min(original, OCR_CONFIDENCE_FLOOR), original * ocr_conf), 3
        )
        flag = compute_quality_flag(confidence)
        if _FLAG_SEVERITY[result.quality_flag] > _FLAG_SEVERITY[flag]:
            flag = result.quality_flag
        adjusted.append(
            replace(
                result,
                extraction_confidence=confidence,
                quality_flag=flag,
                quality_metadata={
                    **result.quality_metadata,
                    "text_source": "ocr",
                    "ocr": dict(ocr),
                    "pre_ocr_confidence": original,
                },
            )
        )
    return adjusted
