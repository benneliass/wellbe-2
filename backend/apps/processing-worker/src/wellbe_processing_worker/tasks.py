from __future__ import annotations

import asyncio
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from wellbe_contracts.c2_vault import RawContextEvent, RAW_CONTEXT_RECEIVED
from wellbe_contracts.c4_processing import (
    FACT_EXTRACTED,
    HEALTH_SIGNAL_CREATED,
    FactExtractedPayload,
)
from wellbe_contracts.c5_evidence import (
    ConfidenceBasis,
    EvidenceLinkType,
    EvidenceRef,
)

_redis_url = os.environ.get("WELLBE_REDIS_URL", "redis://localhost:6379/0")
dramatiq.set_broker(RedisBroker(url=_redis_url))


@dramatiq.actor(max_retries=3, min_backoff=1000, max_backoff=30_000)
def extract_facts_task(event_json: str) -> None:
    """Process a raw_context.received event via lightweight Dramatiq path."""
    asyncio.run(_extract_facts(event_json))


async def _extract_facts(event_json: str) -> None:
    from wellbe_c4_processing import (
        ProcessingRepository,
        TextFactExtractor,
        PIPELINE_VERSION,
    )
    from wellbe_c4_processing.dispatcher import decide_route, DispatchRoute
    from wellbe_c5_evidence import EvidenceService
    from wellbe_events import emit_event
    from wellbe_db import create_session_factory
    from wellbe_processing_worker.config import ProcessingWorkerSettings

    settings = ProcessingWorkerSettings()
    session_factory = create_session_factory(settings.database_url)

    data = json.loads(event_json)
    event = RawContextEvent.model_validate(data)

    decision = decide_route(event.source_type, event.mime_type)
    if decision.route != DispatchRoute.DRAMATIQ_TEXT:
        return

    extractor = TextFactExtractor()

    raw_text = data.get("_raw_text", "")
    if not raw_text and event.blob_ref is None:
        raw_text = data.get("source_metadata", {}).get("text", "")

    results = await extractor.extract(raw_text, event.patient_id)

    async with session_factory() as session:
        repo = ProcessingRepository(session)
        evidence_service = EvidenceService(session)

        for result in results:
            fact_id = uuid.uuid4()
            await repo.insert_fact(
                id=fact_id,
                patient_id=event.patient_id,
                raw_context_event_id=event.id,
                fact_type=result.fact_type.value,
                entity_label=result.entity_label,
                normalized_key=result.normalized_key,
                extraction_confidence=result.extraction_confidence,
                extraction_model=extractor.model_name,
                model_version=extractor.model_version,
                pipeline_version=PIPELINE_VERSION,
                quality_flag=result.quality_flag.value,
                quality_metadata=result.quality_metadata,
                captured_at=event.captured_at,
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
                code_system=result.code_system,
                code=result.code,
                text_span_start=result.text_span_start,
                text_span_end=result.text_span_end,
                source_text_excerpt_hash=(
                    hashlib.sha256(raw_text[result.text_span_start:result.text_span_end].encode()).hexdigest()[:16]
                    if result.text_span_start is not None and result.text_span_end is not None
                    else None
                ),
                is_negated=result.is_negated,
                is_historical=result.is_historical,
                is_hypothetical=result.is_hypothetical,
                subject=result.subject.value,
            )

            await evidence_service.link_fact(
                fact_id=fact_id,
                patient_id=event.patient_id,
                evidence_refs=[EvidenceRef(
                    raw_context_event_id=event.id,
                    link_type=EvidenceLinkType.PRIMARY,
                    confidence=result.extraction_confidence,
                    confidence_basis=ConfidenceBasis.EXTRACTION_MODEL,
                    relevance_span_start=result.text_span_start,
                    relevance_span_end=result.text_span_end,
                )],
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
            )

            payload = FactExtractedPayload(
                fact_id=fact_id,
                patient_id=event.patient_id,
                raw_context_event_id=event.id,
                fact_type=result.fact_type,
                entity_label=result.entity_label,
                normalized_key=result.normalized_key,
                extraction_confidence=result.extraction_confidence,
                quality_flag=result.quality_flag,
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
            )
            await emit_event(
                session=session,
                event_type=FACT_EXTRACTED,
                payload=payload.model_dump(mode="json"),
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
            )

        await session.commit()
