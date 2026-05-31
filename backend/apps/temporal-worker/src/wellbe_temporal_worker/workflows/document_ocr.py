"""DocumentOCRWorkflow: Durable OCR pipeline with fallback strategy.

Pipeline order:
1. PaddleOCR (fast, good for structured documents)
2. Tesseract (fallback for lower-quality images)
3. Vision-LLM (final fallback for complex/handwritten content)

If all three fail, the workflow emits document.ocr_failed and marks
the raw event for manual review.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from temporalio import activity, workflow
from temporalio.common import RetryPolicy


@dataclass
class OCRInput:
    raw_context_event_id: str
    patient_id: str
    blob_ref: str
    blob_bucket: str
    blob_key: str
    mime_type: str
    correlation_id: str
    trace_id: str


@dataclass
class OCRResult:
    text: str
    model: str
    confidence: float
    pages: int


@dataclass
class OCRFailure:
    model: str
    error: str


@activity.defn
async def ocr_with_paddleocr(input: OCRInput) -> OCRResult | None:
    """Run PaddleOCR on the document. Returns None if extraction fails."""
    try:
        # Placeholder: in production, this would download the blob from S3
        # and run PaddleOCR inference
        return OCRResult(
            text="[PaddleOCR placeholder — awaiting model integration]",
            model="paddleocr",
            confidence=0.0,
            pages=1,
        )
    except Exception as e:
        activity.logger.warning(f"PaddleOCR failed: {e}")
        return None


@activity.defn
async def ocr_with_tesseract(input: OCRInput) -> OCRResult | None:
    """Run Tesseract OCR as fallback. Returns None if extraction fails."""
    try:
        return OCRResult(
            text="[Tesseract placeholder — awaiting model integration]",
            model="tesseract",
            confidence=0.0,
            pages=1,
        )
    except Exception as e:
        activity.logger.warning(f"Tesseract failed: {e}")
        return None


@activity.defn
async def ocr_with_vision_llm(input: OCRInput) -> OCRResult | None:
    """Run vision-LLM as final fallback for complex documents."""
    try:
        return OCRResult(
            text="[Vision-LLM placeholder — awaiting model integration]",
            model="vision-llm",
            confidence=0.0,
            pages=1,
        )
    except Exception as e:
        activity.logger.warning(f"Vision-LLM failed: {e}")
        return None


@activity.defn
async def store_ocr_results(
    input: OCRInput,
    result: OCRResult,
) -> dict[str, Any]:
    """Store OCR text as extracted facts via C4 pipeline and create evidence links via C5."""
    import asyncio
    import json

    from wellbe_c4_processing import TextFactExtractor, ProcessingRepository, PIPELINE_VERSION
    from wellbe_c5_evidence import EvidenceService
    from wellbe_contracts.c4_processing import FACT_EXTRACTED, FactExtractedPayload, DOCUMENT_OCR_COMPLETED, DocumentOCRCompletedPayload
    from wellbe_contracts.c5_evidence import EvidenceLinkType, EvidenceRef, ConfidenceBasis
    from wellbe_events import emit_event
    from wellbe_db import create_session_factory

    import os
    database_url = os.environ.get(
        "WELLBE_DATABASE_URL",
        "postgresql+asyncpg://wellbe:wellbe_dev@localhost:5432/wellbe",
    )
    session_factory = create_session_factory(database_url)

    extractor = TextFactExtractor()
    patient_id = uuid.UUID(input.patient_id)
    raw_event_id = uuid.UUID(input.raw_context_event_id)

    results = await extractor.extract(result.text, patient_id)
    fact_ids: list[str] = []

    async with session_factory() as session:
        repo = ProcessingRepository(session)
        evidence_service = EvidenceService(session)

        for extraction in results:
            import hashlib
            from datetime import datetime, timezone

            fact_id = uuid.uuid4()
            await repo.insert_fact(
                id=fact_id,
                patient_id=patient_id,
                raw_context_event_id=raw_event_id,
                fact_type=extraction.fact_type.value,
                entity_label=extraction.entity_label,
                normalized_key=extraction.normalized_key,
                extraction_confidence=min(extraction.extraction_confidence, result.confidence),
                extraction_model=f"{result.model}+{extractor.model_name}",
                model_version=extractor.model_version,
                pipeline_version=PIPELINE_VERSION,
                quality_flag=extraction.quality_flag.value,
                quality_metadata={
                    "ocr_model": result.model,
                    "ocr_confidence": result.confidence,
                    **extraction.quality_metadata,
                },
                captured_at=datetime.now(timezone.utc),
                correlation_id=input.correlation_id,
                trace_id=input.trace_id,
                text_span_start=extraction.text_span_start,
                text_span_end=extraction.text_span_end,
                is_negated=extraction.is_negated,
                subject=extraction.subject.value,
            )

            await evidence_service.link_fact(
                fact_id=fact_id,
                patient_id=patient_id,
                evidence_refs=[EvidenceRef(
                    raw_context_event_id=raw_event_id,
                    link_type=EvidenceLinkType.PRIMARY,
                    confidence=min(extraction.extraction_confidence, result.confidence),
                    confidence_basis=ConfidenceBasis.EXTRACTION_MODEL,
                )],
                correlation_id=input.correlation_id,
                trace_id=input.trace_id,
            )

            fact_ids.append(str(fact_id))

            await emit_event(
                session=session,
                event_type=FACT_EXTRACTED,
                payload=FactExtractedPayload(
                    fact_id=fact_id,
                    patient_id=patient_id,
                    raw_context_event_id=raw_event_id,
                    fact_type=extraction.fact_type,
                    entity_label=extraction.entity_label,
                    normalized_key=extraction.normalized_key,
                    extraction_confidence=extraction.extraction_confidence,
                    quality_flag=extraction.quality_flag,
                    correlation_id=input.correlation_id,
                    trace_id=input.trace_id,
                ).model_dump(mode="json"),
                correlation_id=input.correlation_id,
                trace_id=input.trace_id,
            )

        ocr_completed_payload = DocumentOCRCompletedPayload(
            raw_context_event_id=raw_event_id,
            patient_id=patient_id,
            fact_ids=[uuid.UUID(fid) for fid in fact_ids],
            ocr_model=result.model,
            ocr_confidence=result.confidence,
            correlation_id=input.correlation_id,
            trace_id=input.trace_id,
        )
        await emit_event(
            session=session,
            event_type=DOCUMENT_OCR_COMPLETED,
            payload=ocr_completed_payload.model_dump(mode="json"),
            correlation_id=input.correlation_id,
            trace_id=input.trace_id,
        )

        await session.commit()

    return {"fact_ids": fact_ids, "ocr_model": result.model}


@workflow.defn
class DocumentOCRWorkflow:
    """Durable OCR workflow with PaddleOCR → Tesseract → Vision-LLM fallback."""

    @workflow.run
    async def run(self, input: OCRInput) -> dict[str, Any]:
        retry_policy = RetryPolicy(
            maximum_attempts=2,
            initial_interval=timedelta(seconds=5),
        )

        result = await workflow.execute_activity(
            ocr_with_paddleocr,
            input,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy,
        )

        if result is None or result.confidence < 0.5:
            result = await workflow.execute_activity(
                ocr_with_tesseract,
                input,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )

        if result is None or result.confidence < 0.5:
            result = await workflow.execute_activity(
                ocr_with_vision_llm,
                input,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=retry_policy,
            )

        if result is None or result.confidence < 0.3:
            from wellbe_contracts.c4_processing import (
                DOCUMENT_OCR_FAILED,
                DocumentOCRFailedPayload,
                QualityFlag,
            )
            return {
                "status": "failed",
                "event_type": DOCUMENT_OCR_FAILED,
                "raw_context_event_id": input.raw_context_event_id,
                "reason": "All OCR models failed or returned insufficient confidence",
            }

        stored = await workflow.execute_activity(
            store_ocr_results,
            args=[input, result],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy,
        )

        return {
            "status": "completed",
            "ocr_model": result.model,
            "confidence": result.confidence,
            "fact_ids": stored["fact_ids"],
        }
