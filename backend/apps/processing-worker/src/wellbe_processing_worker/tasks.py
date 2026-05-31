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
import wellbe_c2_vault.models  # noqa: F401 — ensure vault tables registered in Base.metadata
from wellbe_contracts.c4_processing import (
    FACT_EXTRACTED,
    HEALTH_SIGNAL_CREATED,
    FactExtractedPayload,
)
from wellbe_contracts.c5_evidence import (
    ConfidenceBasis,
    EvidenceLinkType,
    EvidenceRef,
    EvidenceLinkedPayload,
    EVIDENCE_LINKED,
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
    from wellbe_db import create_engine, create_session_factory
    from wellbe_processing_worker.config import ProcessingWorkerSettings

    settings = ProcessingWorkerSettings()
    session_factory = create_session_factory(create_engine(settings.database_url))

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
                captured_at=event.captured_at.replace(tzinfo=None) if event.captured_at.tzinfo else event.captured_at,
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

    # Wire graph node creation directly (no separate Dramatiq worker running)
    for result in results:
        fact_payload = FactExtractedPayload(
            fact_id=uuid.uuid4(),  # approximate; node upsert is idempotent on normalized_key
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
        await _create_graph_node(fact_payload.model_dump_json())


FACT_TYPE_TO_NODE_TYPE: dict[str, str] = {
    "symptom": "Symptom",
    "finding": "ConditionHypothesis",
    "medication": "Medication",
    "lab_result": "LabResult",
    "allergy": "Allergy",
    "procedure": "Procedure",
    "dx_mention": "ConditionHypothesis",
    "vital_sign": "VitalSign",
    "immunization": "Immunization",
    "family_history": "FamilyHistory",
    "social_history": "SocialFactor",
    "other": "Other",
}


@dramatiq.actor(max_retries=3, min_backoff=1000, max_backoff=30_000)
def create_graph_node_task(fact_extracted_json: str) -> None:
    """Create/upsert a KG node from a fact.extracted event."""
    asyncio.run(_create_graph_node(fact_extracted_json))


async def _create_graph_node(fact_extracted_json: str) -> None:
    from wellbe_c6_graph import GraphRepository
    from wellbe_events import emit_event
    from wellbe_db import create_engine, create_session_factory
    from wellbe_processing_worker.config import ProcessingWorkerSettings

    settings = ProcessingWorkerSettings()
    session_factory = create_session_factory(create_engine(settings.database_url))

    data = json.loads(fact_extracted_json)
    payload = FactExtractedPayload.model_validate(data)

    node_type = FACT_TYPE_TO_NODE_TYPE.get(payload.fact_type.value, "Other")

    async with session_factory() as session:
        repo = GraphRepository(session)
        node = await repo.upsert_node(
            patient_id=payload.patient_id,
            node_type=node_type,
            normalized_key=payload.normalized_key,
            display_label=payload.entity_label,
        )

        await emit_event(
            session=session,
            event_type="graph.node_created",
            payload={
                "node_id": str(node.id),
                "patient_id": str(payload.patient_id),
                "node_type": node_type,
                "normalized_key": payload.normalized_key,
                "fact_id": str(payload.fact_id),
            },
            correlation_id=payload.correlation_id,
            trace_id=payload.trace_id,
        )

        await session.commit()


@dramatiq.actor(max_retries=3, min_backoff=1000, max_backoff=30_000)
def score_graph_edges_task(evidence_linked_json: str) -> None:
    """Score/rescore edges when new evidence is linked."""
    asyncio.run(_score_graph_edges(evidence_linked_json))


async def _score_graph_edges(evidence_linked_json: str) -> None:
    from wellbe_c6_graph import GraphRepository, PotentialScoreComputer, ScoreInput
    from wellbe_events import emit_event
    from wellbe_db import create_engine, create_session_factory
    from wellbe_processing_worker.config import ProcessingWorkerSettings

    settings = ProcessingWorkerSettings()
    session_factory = create_session_factory(create_engine(settings.database_url))

    data = json.loads(evidence_linked_json)
    payload = EvidenceLinkedPayload.model_validate(data)

    async with session_factory() as session:
        repo = GraphRepository(session)
        scorer = PotentialScoreComputer()

        edges = await repo.get_edges_needing_rescore(limit=50)
        for edge in edges:
            score_input = ScoreInput(
                link_type=payload.link_type,
                confidence=payload.confidence,
                edge_category=edge.edge_type,
            )
            result = scorer.compute([score_input])

            edge.potential_score = result.potential_score
            edge.score_version = result.score_version
            edge.score_inputs = result.score_inputs
            edge.needs_rescore = False
            edge.updated_at = datetime.now(timezone.utc)

            await emit_event(
                session=session,
                event_type="graph.edge_scored",
                payload={
                    "edge_id": str(edge.id),
                    "patient_id": str(edge.patient_id),
                    "potential_score": result.potential_score,
                    "score_version": result.score_version,
                },
                correlation_id=payload.correlation_id,
                trace_id=payload.trace_id,
            )

        await session.commit()
